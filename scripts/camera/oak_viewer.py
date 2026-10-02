"""Preview live de l'OAK-D Lite via le flux ZMQ de oak_zmq_server.py. Affiche résolution/fps réel à l'écran.
Nécessite oak_zmq_server.py lancé en parallèle (voir scripts/shell/calibrate_with_oak.sh pour le pattern)."""

import sys

from camera_utils import ZMQCamera, live_view


def main():
    cap = ZMQCamera()
    cap.open()
    if not cap.isOpened():
        print("Erreur: OAK-D Lite inaccessible via ZMQ (oak_zmq_server.py est-il lancé ?).", file=sys.stderr)
        sys.exit(1)

    # 15 lectures ratées d'affilée (~30s à 2s/lecture) : couvre le warm-up du serveur
    # (10 frames jetées avant publication) même à FPS bas, pas juste une vraie coupure.
    live_view(cap, "Viewer OAK-D Lite  |  Q=quitter", max_consecutive_misses=15)


if __name__ == "__main__":
    main()
