#!/usr/bin/env python3
"""Client MQTT pour recevoir les consignes RobotKraft. Dédoublonne automatiquement par
`id` : un message déjà vu (rejoué par le `retain` du broker) est ignoré silencieusement,
seule une consigne inédite est remontée."""

import json
import os
import sys
import threading
from queue import Empty, Queue

import paho.mqtt.client as mqtt

HOTE_TCP = "mqtt.teleport.francsducloud.wtf"
PORT_TCP = 443  # MQTT sur TLS, port 443 (pas 8883) pour passer les WiFi d'évènement filtrés

HOTE_WS = "mqtt-ws.teleport.francsducloud.wtf"
PORT_WS = 443  # wss, repli si le port TCP ci-dessus est bloqué sur le réseau du lieu


class ErreurMQTT(Exception):
    """Levée pour toute erreur de connexion/configuration compréhensible par un participant
    (identifiants refusés, broker injoignable, équipe manquante...)."""


class _Dedupliqueur:
    """Mémorise les `id` de consigne déjà vus. C'est la seule logique non triviale du
    module : le broker republie le dernier message (`retain`) à chaque (re)connexion ou
    (ré)abonnement, y compris un message d'un test antérieur."""

    def __init__(self):
        self._vus = set()

    def est_nouvelle(self, id_message):
        if id_message in self._vus:
            return False
        self._vus.add(id_message)
        return True


class RecepteurConsigne:
    """Reçoit les consignes RobotKraft d'une équipe sur `robotkraft/<equipe>/consigne`.

    Usage bloquant, le plus simple :
        recepteur = RecepteurConsigne("equipe07", mot_de_passe)
        recepteur.connecter()
        consigne = recepteur.attendre_consigne()   # bloque jusqu'à la prochaine consigne inédite
        print(consigne["epreuve"], consigne["consigne"])

    Usage par callback, pour une boucle robot qui tourne déjà en continu :
        recepteur = RecepteurConsigne("equipe07", mot_de_passe)
        recepteur.sur_consigne(lambda msg: print("nouvelle consigne :", msg))
        recepteur.connecter()
        ...
        recepteur.arreter()

    Le compte et le mot de passe ne sont jamais à écrire en dur dans le code : les
    passer en paramètre, ou via les variables d'environnement ROBOTKRAFT_MQTT_EQUIPE /
    ROBOTKRAFT_MQTT_PASSWORD.
    """

    def __init__(self, equipe=None, mot_de_passe=None, *, transport="tcp"):
        equipe = equipe or os.environ.get("ROBOTKRAFT_MQTT_EQUIPE")
        mot_de_passe = mot_de_passe or os.environ.get("ROBOTKRAFT_MQTT_PASSWORD")
        if not equipe:
            raise ErreurMQTT(
                "Compte équipe manquant : passe-le en paramètre (ex. \"equipe07\") ou via "
                "la variable d'environnement ROBOTKRAFT_MQTT_EQUIPE."
            )
        if not mot_de_passe:
            raise ErreurMQTT(
                "Mot de passe manquant : passe-le en paramètre, ou via la variable "
                "d'environnement ROBOTKRAFT_MQTT_PASSWORD (celui transmis par l'organisation)."
            )
        if transport not in ("tcp", "websockets"):
            raise ErreurMQTT('transport doit être "tcp" (défaut) ou "websockets".')

        self.equipe = equipe
        self._topic = f"robotkraft/{equipe}/consigne"
        self._dedup = _Dedupliqueur()
        self._queue = Queue()
        self._callback = None
        self._connecte = threading.Event()
        self._erreur_connexion = None

        self._hote = HOTE_WS if transport == "websockets" else HOTE_TCP
        self._port = PORT_WS if transport == "websockets" else PORT_TCP

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="", transport=transport
        )
        self._client.username_pw_set(equipe, mot_de_passe)
        self._client.tls_set()  # certificat Let's Encrypt, public, rien à fournir
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def sur_consigne(self, callback):
        """Enregistre `callback(consigne: dict)`, appelée pour chaque consigne inédite."""
        self._callback = callback

    def connecter(self, timeout=10):
        """Se connecte au broker et attend la confirmation. Lève ErreurMQTT si le réseau
        ou les identifiants posent problème, plutôt qu'une exception brute de paho-mqtt."""
        try:
            self._client.connect(self._hote, self._port, keepalive=60)
        except Exception as e:
            raise ErreurMQTT(
                f"Impossible de joindre le broker MQTT ({self._hote}:{self._port}) : {e}. "
                "Vérifie ta connexion réseau."
            ) from e

        self._client.loop_start()
        if not self._connecte.wait(timeout):
            self._client.loop_stop()
            raise ErreurMQTT(
                f"Pas de réponse du broker après {timeout}s. Réseau filtré (essaie "
                'transport="websockets") ou broker indisponible.'
            )
        if self._erreur_connexion is not None:
            self._client.loop_stop()
            raise self._erreur_connexion
        return self

    def attendre_consigne(self, timeout=None):
        """Bloque jusqu'à la prochaine consigne inédite (par `id`) et la retourne en entier
        (`epreuve`, `variante`, `id`, `consigne`). Lève TimeoutError si `timeout` est dépassé."""
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"Aucune nouvelle consigne reçue après {timeout}s.")

    def arreter(self):
        """Ferme proprement la connexion (ne tente plus de se reconnecter ensuite)."""
        self._client.disconnect()
        self._client.loop_stop()

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            self._erreur_connexion = ErreurMQTT(
                f"Connexion refusée par le broker pour \"{self.equipe}\" : {reason_code}. "
                "Vérifie le compte et le mot de passe transmis par l'organisation."
            )
            self._connecte.set()
            client.disconnect()  # pas de ré-essai en boucle sur un mot de passe faux
            return
        client.subscribe(self._topic)
        self._connecte.set()

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if reason_code.is_failure and self._erreur_connexion is None:
            print("[robotkraft_mqtt] Connexion perdue, reconnexion automatique en cours...", file=sys.stderr)

    def _on_message(self, client, userdata, msg):
        try:
            message = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[robotkraft_mqtt] Message illisible sur {msg.topic}, ignoré : {e}", file=sys.stderr)
            return
        id_message = message.get("id")
        if id_message is None:
            print(f"[robotkraft_mqtt] Message sans champ 'id' sur {msg.topic}, ignoré.", file=sys.stderr)
            return
        if not self._dedup.est_nouvelle(id_message):
            return  # déjà vu (rejoué par retain), on ignore silencieusement
        self._queue.put(message)
        if self._callback is not None:
            self._callback(message)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        d = _Dedupliqueur()
        assert d.est_nouvelle("t1-001") is True, "une id jamais vue doit être acceptée"
        assert d.est_nouvelle("t1-001") is False, "une id déjà vue doit être rejetée (message retain rejoué)"
        assert d.est_nouvelle("t1-002") is True, "une id différente reste acceptée"
        assert d.est_nouvelle("t1-002") is False, "idempotence : un deuxième doublon reste rejeté"
        print("self-test OK")
    else:
        print(__doc__)
        print("\nVoir scripts/mqtt/exemple_reception.py pour un exemple d'utilisation.")
