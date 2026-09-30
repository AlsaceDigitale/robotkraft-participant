"""Enregistre une trajectoire : suit le bras leader en téléop et sauvegarde les positions follower à intervalle régulier dans un fichier .npy"""

import os, time, signal
import numpy as np
from lerobot.motors.feetech import FeetechMotorsBus
from safety import write_safe, configure_gripper
from motors_config import MOTORS
from config import HZ, FOLLOW_HZ

LEADER_PORT = os.environ.get("LEADER_PORT", "/dev/ttyACM1")
FOLLOWER_PORT = os.environ.get("FOLLOWER_PORT", "/dev/ttyACM0")
TRAJ_FILE = os.environ.get("TRAJ_FILE", "/workspace/datasets/trajectory.npy")
os.makedirs(os.path.dirname(TRAJ_FILE), exist_ok=True)
DURATION = float(os.environ.get("DURATION", 0))  # 0 = jusqu'à Ctrl+C

leader = FeetechMotorsBus(port=LEADER_PORT, motors=MOTORS)
follower = FeetechMotorsBus(port=FOLLOWER_PORT, motors=MOTORS)
leader.connect()
follower.connect()
configure_gripper(follower)

frames = []
running = True


def stop(sig, frame):
    """Handler SIGINT (Ctrl+C), arrête l'enregistrement proprement"""
    global running
    running = False


signal.signal(signal.SIGINT, stop)
label = f"{DURATION}s" if DURATION else "infini (Ctrl+C pour arrêter)"
print(f"Enregistrement à {HZ}Hz (suivi à {FOLLOW_HZ}Hz) - {label}")

# Suivi leader->follower à FOLLOW_HZ pour un mouvement fluide, mais sauvegarde à HZ pour garder le format de fichier existant.
record_every = FOLLOW_HZ // HZ
dt = 1.0 / FOLLOW_HZ
i = 0
t_start = time.perf_counter()
try:
    while running and (DURATION == 0 or time.perf_counter() - t_start < DURATION):
        t0 = time.perf_counter()
        try:
            pos_dict = leader.sync_read("Present_Position", normalize=False)
            positions = [pos_dict[name] for name in MOTORS]
        except Exception as e:
            print(f"[WARN] sync_read leader échouée ({e}) - frame ignorée")
            elapsed = time.perf_counter() - t0
            time.sleep(max(0, dt - elapsed))
            continue
        write_safe(follower, list(MOTORS), positions)
        if i % record_every == 0:
            frames.append(positions)
        i += 1
        elapsed = time.perf_counter() - t0
        time.sleep(max(0, dt - elapsed))
finally:
    if frames:
        np.save(TRAJ_FILE, np.array(frames, dtype=np.int32))
        print(f"{len(frames)} frames sauvegardées ({len(frames)/HZ:.1f}s) dans {TRAJ_FILE}")
    else:
        print("Aucune frame enregistrée - fichier non sauvegardé.")
    leader.disconnect()
    follower.disconnect()
