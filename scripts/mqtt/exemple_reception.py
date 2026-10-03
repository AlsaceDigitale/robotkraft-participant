#!/usr/bin/env python3
"""Exemple d'utilisation de RecepteurConsigne. Aucun identifiant en dur : le compte et le
mot de passe transmis par l'organisation viennent des variables d'environnement.

    export ROBOTKRAFT_MQTT_EQUIPE=equipe07
    export ROBOTKRAFT_MQTT_PASSWORD=...        # reçu par mail, à ne jamais committer
    python3 scripts/mqtt/exemple_reception.py
"""

from robotkraft_mqtt import ErreurMQTT, RecepteurConsigne

try:
    recepteur = RecepteurConsigne()  # lit ROBOTKRAFT_MQTT_EQUIPE / ROBOTKRAFT_MQTT_PASSWORD
    recepteur.connecter()
except ErreurMQTT as e:
    print(f"Erreur : {e}")
    raise SystemExit(1)

print(f"Connecté, en attente de la consigne pour {recepteur.equipe}...")

# Mode 1 : bloquant, pour un script qui a juste besoin de la consigne avant de démarrer.
consigne = recepteur.attendre_consigne()
print(f"Épreuve {consigne['epreuve']} (variante {consigne['variante']}) : {consigne['consigne']}")

# Mode 2 : callback, pour une boucle robot qui tourne déjà et doit juste réagir à une
# nouvelle consigne pendant qu'elle tourne (ex. changement d'épreuve en cours de session) :
#
#     def sur_nouvelle_consigne(message):
#         print("nouvelle consigne reçue :", message["consigne"])
#
#     recepteur.sur_consigne(sur_nouvelle_consigne)
#     while robot_en_marche:
#         ...  # la callback est appelée en tâche de fond à chaque nouvelle consigne

recepteur.arreter()
