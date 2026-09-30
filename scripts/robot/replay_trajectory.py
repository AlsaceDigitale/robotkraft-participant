"""Rejoue une trajectoire .npy unique enregistrée précédemment en interpolant entre frames pour un mouvement fluide"""

import os, signal
import numpy as np
from lerobot.motors.feetech import FeetechMotorsBus
from motors_config import MOTORS
from motion_utils import running, stop, interp_move
from safety import write_safe, configure_gripper
from config import HZ, INTERP_HZ

FOLLOWER_PORT = os.environ.get("FOLLOWER_PORT", "/dev/ttyACM0")
TRAJ_FILE = os.environ.get("TRAJ_FILE", "/workspace/datasets/trajectory.npy")

frames = np.load(TRAJ_FILE)
motor_names = list(MOTORS.keys())

print(f"{len(frames)} frames chargées ({len(frames)/HZ:.1f}s) depuis {TRAJ_FILE}")
print(f"Position de départ (ticks bruts) : {dict(zip(motor_names, frames[0]))}")
input("Positionner le bras follower approximativement à la position de départ, puis appuyer sur Entrée...")

signal.signal(signal.SIGINT, stop)

follower = FeetechMotorsBus(port=FOLLOWER_PORT, motors=MOTORS)
follower.connect()
configure_gripper(follower)

try:
    lw_dict = follower.sync_read("Present_Position", normalize=False)
    last_written = {name: lw_dict[name] for name in motor_names}

    current = np.array([last_written[name] for name in motor_names], dtype=float)
    target = frames[0].astype(float)
    # 200 pas fixes (indépendants de INTERP_HZ)
    GOTO_STEPS = 200
    print("Mouvement vers position de départ... (Ctrl+C pour interrompre)")
    interp_move(follower, motor_names, current, target, GOTO_STEPS, 0.01, inclusive=True)

    n_interp = INTERP_HZ // HZ
    dt = 1.0 / INTERP_HZ

    for i in range(len(frames) - 1):
        if not running[0]:
            break
        interp_move(follower, motor_names, frames[i], frames[i + 1], n_interp, dt)

    if running[0]:
        write_safe(follower, motor_names, frames[-1])
        print("Replay terminé.")
    else:
        print("Replay interrompu (Ctrl+C).")
finally:
    follower.disconnect()
