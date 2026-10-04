#!/usr/bin/env python3
"""Usage example for InstructionReceiver. No hardcoded credentials: the account and
password handed out by the organization come from environment variables.

    export ROBOTKRAFT_MQTT_EQUIPE=equipe07
    export ROBOTKRAFT_MQTT_PASSWORD=...        # reçu par mail, à ne jamais committer
    python3 scripts/mqtt/example_reception.py
"""

from robotkraft_mqtt import InstructionReceiver, MQTTError

try:
    receiver = InstructionReceiver()  # reads ROBOTKRAFT_MQTT_EQUIPE / ROBOTKRAFT_MQTT_PASSWORD
    receiver.connect()
except MQTTError as e:
    print(f"Erreur : {e}")
    raise SystemExit(1)

print(f"Connecté, en attente de la consigne pour {receiver.team}...")

# Mode 1: blocking, for a script that just needs the instruction before it starts.
instruction = receiver.wait_for_instruction()
print(f"Épreuve {instruction['epreuve']} (variante {instruction['variante']}) : {instruction['consigne']}")

# Mode 2: callback, for a robot loop that's already running and just needs to react to
# a new instruction while it runs (e.g. a challenge change mid-session):
#
#     def on_new_instruction(message):
#         print("nouvelle consigne reçue :", message["consigne"])
#
#     receiver.on_instruction(on_new_instruction)
#     while robot_running:
#         ...  # the callback is called in the background on each new instruction

receiver.stop()
