"""Vérifie que chaque port série correspond bien au bras attendu (follower/leader) en tentant une connexion moteur test sur /dev/ttyACM0 et /dev/ttyACM1"""

from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors.motors_bus import Motor, MotorNormMode

for port, name in [("/dev/ttyACM0", "follower"), ("/dev/ttyACM1", "leader")]:
    try:
        bus = FeetechMotorsBus(
            port=port,
            motors={"j1": Motor(id=1, model="sts3215", norm_mode=MotorNormMode.DEGREES)},
        )
        bus.connect()
        print(f"{port} -> {name} OK")
        bus.disconnect()
    except Exception as e:
        print(f"{port} -> {name} ERREUR: {e}")
