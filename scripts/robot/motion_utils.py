"""Utilitaires de mouvement interpolé (lissage entre positions) partagés par les scripts de replay/record, flag d'arrêt propre sur Ctrl+C"""

import time
import numpy as np
from safety import write_safe
from config import HZ, INTERP_HZ

running = [True]


def stop(sig, frame):
    """Handler SIGINT (Ctrl+C), bascule running à False pour interrompre proprement une boucle en cours"""
    running[0] = False


def interp_move(follower, motor_names, start, end, n_steps, dt, inclusive=False):
    """Déplace le follower de start à end en n_steps pas linéairement interpolés à intervalle dt, évite les à-coups moteur d'un saut de position brut"""
    count = n_steps + 1 if inclusive else n_steps
    for k in range(count):
        if not running[0]:
            return
        t0 = time.perf_counter()
        alpha = k / n_steps
        pos = start + alpha * (end - start)
        write_safe(follower, motor_names, pos)
        elapsed = time.perf_counter() - t0
        time.sleep(max(0, dt - elapsed))


def replay_traj_file(follower, motor_names, traj_path, last_written):
    """Charge une trajectoire .npy et la rejoue frame par frame (interpolée) en partant de last_written (dernière position réellement écrite sur le bus)"""
    frames = np.load(traj_path)
    current = np.array([last_written[name] for name in motor_names], dtype=float)
    # Premier mouvement (200 pas / 0.01s) : va de la position actuelle du bras à la première frame enregistrée
    interp_move(follower, motor_names, current, frames[0].astype(float), 200, 0.01, inclusive=True)
    # Trajectoire enregistrée à HZ (10) mais rejouée interpolée à INTERP_HZ (100)
    n_interp = INTERP_HZ // HZ
    dt = 1.0 / INTERP_HZ
    for i in range(len(frames) - 1):
        if not running[0]:
            return
        interp_move(follower, motor_names, frames[i].astype(float), frames[i + 1].astype(float), n_interp, dt)
    if running[0]:
        write_safe(follower, motor_names, frames[-1])
        for name, val in zip(motor_names, frames[-1]):
            last_written[name] = int(val)
