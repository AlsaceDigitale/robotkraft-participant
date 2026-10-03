#!/usr/bin/env python3
"""MQTT client for receiving RobotKraft instructions. Automatically deduplicates by
`id`: a message already seen (replayed by the broker's `retain`) is silently ignored,
only a new instruction is surfaced."""

import json
import os
import sys
import threading
from queue import Empty, Queue

import paho.mqtt.client as mqtt

HOST_TCP = "mqtt.teleport.francsducloud.wtf"
PORT_TCP = 443  # MQTT over TLS, port 443 (not 8883) to get through filtered event WiFi

HOST_WS = "mqtt-ws.teleport.francsducloud.wtf"
PORT_WS = 443  # wss, fallback if the TCP port above is blocked on the venue's network

_REQUIRED_FIELDS = ("epreuve", "variante", "id", "consigne")  # format imposed by the organization


class MQTTError(Exception):
    """Raised for any connection/configuration error meant to be understandable by a
    participant (refused credentials, unreachable broker, missing team...)."""


class _Deduplicator:
    """Remembers which instruction `id`s have already been seen. This is the only
    non-trivial logic in the module: the broker republishes the last message (`retain`)
    on every (re)connection or (re)subscription, including a message from an earlier
    test."""

    def __init__(self):
        self._seen = set()

    def is_new(self, message_id):
        if message_id in self._seen:
            return False
        self._seen.add(message_id)
        return True


class InstructionReceiver:
    """Receives RobotKraft instructions for a team on `robotkraft/<team>/consigne`.

    Simplest, blocking usage:
        receiver = InstructionReceiver("equipe07", password)
        receiver.connect()
        instruction = receiver.wait_for_instruction()   # blocks until the next new instruction
        print(instruction["epreuve"], instruction["consigne"])

    Callback usage, for a robot loop that's already running continuously:
        receiver = InstructionReceiver("equipe07", password)
        receiver.on_instruction(lambda msg: print("new instruction:", msg))
        receiver.connect()
        ...
        receiver.stop()

    The account and password must never be hardcoded: pass them as parameters, or via
    the ROBOTKRAFT_MQTT_EQUIPE / ROBOTKRAFT_MQTT_PASSWORD environment variables.
    """

    def __init__(self, team=None, password=None, *, transport="tcp"):
        team = team or os.environ.get("ROBOTKRAFT_MQTT_EQUIPE")
        password = password or os.environ.get("ROBOTKRAFT_MQTT_PASSWORD")
        if not team:
            raise MQTTError(
                "Compte équipe manquant : passe-le en paramètre (ex. \"equipe07\") ou via "
                "la variable d'environnement ROBOTKRAFT_MQTT_EQUIPE."
            )
        if not password:
            raise MQTTError(
                "Mot de passe manquant : passe-le en paramètre, ou via la variable "
                "d'environnement ROBOTKRAFT_MQTT_PASSWORD (celui transmis par l'organisation)."
            )
        if transport not in ("tcp", "websockets"):
            raise MQTTError('transport doit être "tcp" (défaut) ou "websockets".')

        self.team = team
        self._topic = f"robotkraft/{team}/consigne"
        self._deduplicator = _Deduplicator()
        self._queue = Queue()
        self._callback = None
        self._connected = threading.Event()
        self._connection_error = None
        self._subscription_mid = None

        self._host = HOST_WS if transport == "websockets" else HOST_TCP
        self._port = PORT_WS if transport == "websockets" else PORT_TCP

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="", transport=transport
        )
        self._client.username_pw_set(team, password)
        self._client.tls_set()  # Let's Encrypt certificate, public, nothing to provide
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_subscribe = self._on_subscribe
        self._client.on_message = self._on_message

    def on_instruction(self, callback):
        """Registers `callback(instruction: dict)`, called for each new instruction."""
        self._callback = callback

    def connect(self, timeout=10):
        """Connects to the broker and waits for confirmation (CONNACK + accepted
        subscription). Raises MQTTError on network, credentials or subscription issues,
        instead of a raw paho-mqtt exception."""
        # Reset on every call: otherwise a connect() after a failure, or after stop(),
        # would reuse the previous attempt's state (success or error).
        self._connected.clear()
        self._connection_error = None
        try:
            self._client.connect(self._host, self._port, keepalive=60)
        except Exception as e:
            raise MQTTError(
                f"Impossible de joindre le broker MQTT ({self._host}:{self._port}) : {e}. "
                "Vérifie ta connexion réseau."
            ) from e

        self._client.loop_start()
        if not self._connected.wait(timeout):
            self._client.loop_stop()
            raise MQTTError(
                f"Pas de réponse du broker après {timeout}s. Réseau filtré (essaie "
                'transport="websockets") ou broker indisponible.'
            )
        if self._connection_error is not None:
            self._client.loop_stop()
            raise self._connection_error
        return self

    def wait_for_instruction(self, timeout=None):
        """Blocks until the next new instruction (by `id`) and returns it whole
        (`epreuve`, `variante`, `id`, `consigne`). Raises TimeoutError if `timeout` is
        exceeded."""
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"Aucune nouvelle consigne reçue après {timeout}s.")

    def stop(self):
        """Closes the connection cleanly (no further reconnection attempts)."""
        self._client.disconnect()
        self._client.loop_stop()

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            self._connection_error = MQTTError(
                f"Connexion refusée par le broker pour \"{self.team}\" : {reason_code}. "
                "Vérifie le compte et le mot de passe transmis par l'organisation."
            )
            self._connected.set()
            client.disconnect()  # no retry loop on a wrong password
            return
        # No self._connected.set() here: subscribe() only sends the request, it's
        # on_subscribe (SUBACK) that confirms we're actually ready to receive.
        result, mid = client.subscribe(self._topic)
        if result != mqtt.MQTT_ERR_SUCCESS:
            self._connection_error = MQTTError(f"Échec de l'abonnement à {self._topic} (code {result}).")
            self._connected.set()
            return
        self._subscription_mid = mid

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if reason_code.is_failure and self._connection_error is None:
            print("[robotkraft_mqtt] Connexion perdue, reconnexion automatique en cours...", file=sys.stderr)

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        if mid != self._subscription_mid:
            return  # SUBACK for a previous subscription (already superseded by a reconnect), ignored
        failed = [rc for rc in reason_code_list if rc.is_failure]
        if failed:
            error = MQTTError(
                f"Abonnement à {self._topic} refusé par le broker : "
                f"{', '.join(str(rc) for rc in failed)}."
            )
            if self._connected.is_set():
                # Mid-session reconnect: connect() has already returned, nobody will
                # read _connection_error anymore, just report it.
                print(f"[robotkraft_mqtt] {error}", file=sys.stderr)
            else:
                self._connection_error = error
        self._connected.set()

    def _on_message(self, client, userdata, msg):
        # A crash here would kill paho's network thread (reconnection included): this
        # whole method must stay unbreakable, even on a malformed message or a
        # participant callback that raises.
        try:
            message = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[robotkraft_mqtt] Message illisible sur {msg.topic}, ignoré : {e}", file=sys.stderr)
            return
        if not isinstance(message, dict) or any(f not in message for f in _REQUIRED_FIELDS):
            print(
                f"[robotkraft_mqtt] Message incomplet sur {msg.topic} (attendu : "
                f"{', '.join(_REQUIRED_FIELDS)}), ignoré.",
                file=sys.stderr,
            )
            return
        message_id = message["id"]
        if not isinstance(message_id, (str, int, float)):
            print(f"[robotkraft_mqtt] Champ 'id' inexploitable sur {msg.topic}, ignoré.", file=sys.stderr)
            return
        # Validated before deduplication: an incomplete message must not "consume" the
        # id and block the corrected version that would later arrive with the same id.
        if not self._deduplicator.is_new(message_id):
            return  # already seen (replayed by retain), silently ignored
        self._queue.put(message)
        if self._callback is not None:
            try:
                self._callback(message)
            except Exception as e:
                print(f"[robotkraft_mqtt] Erreur dans la callback on_instruction, ignorée : {e}", file=sys.stderr)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        d = _Deduplicator()
        assert d.is_new("t1-001") is True, "a never-seen id must be accepted"
        assert d.is_new("t1-001") is False, "an already-seen id must be rejected (replayed retain message)"
        assert d.is_new("t1-002") is True, "a different id is still accepted"
        assert d.is_new("t1-002") is False, "idempotence: a second duplicate is still rejected"
        print("self-test OK")
    else:
        print("RobotKraft : bibliothèque de réception MQTT des consignes.")
        print("Voir scripts/mqtt/example_reception.py pour un exemple d'utilisation.")
