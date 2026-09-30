"""Rejoue une séquence de plusieurs trajectoires définies dans un fichier JSON, avec pause entre chaque"""

import os, time, signal, json
from lerobot.motors.feetech import FeetechMotorsBus
from motors_config import MOTORS
from motion_utils import running, stop, replay_traj_file
from safety import configure_gripper

FOLLOWER_PORT = os.environ.get("FOLLOWER_PORT", "/dev/ttyACM0")
SEQUENCE_FILE = os.environ.get("SEQUENCE_FILE", "/workspace/datasets/sequences/sequence.json")

signal.signal(signal.SIGINT, stop)

with open(SEQUENCE_FILE) as f:
    seq = json.load(f)

base_dir = os.path.dirname(os.path.abspath(SEQUENCE_FILE))
trajectories = seq["trajectories"]
pause_s = seq.get("pause_between_s", 1.0)

motor_names = list(MOTORS.keys())

follower = FeetechMotorsBus(port=FOLLOWER_PORT, motors=MOTORS)
follower.connect()
configure_gripper(follower)

try:
    lw_dict = follower.sync_read("Present_Position", normalize=False)
    last_written = {name: lw_dict[name] for name in motor_names}

    print(f"Séquence: {len(trajectories)} trajectoires, pause={pause_s}s entre chaque")
    input("Positionner le bras à la position initiale, puis Entrée...")

    for i, traj_name in enumerate(trajectories):
        if not running[0]:
            break
        traj_path = traj_name if os.path.isabs(traj_name) else os.path.join(base_dir, traj_name)
        print(f"[{i + 1}/{len(trajectories)}] {traj_name}")
        replay_traj_file(follower, motor_names, traj_path, last_written)

        if running[0] and i < len(trajectories) - 1:
            print(f"  pause {pause_s}s...")
            time.sleep(pause_s)

    if running[0]:
        print("Séquence terminée.")
    else:
        print("Séquence interrompue (Ctrl+C).")
finally:
    follower.disconnect()
