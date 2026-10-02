"""Preview live d'une webcam USB générique (ET-S231 et similaires) via V4L2. Affiche résolution/fps réel à l'écran"""

import os
import sys

from camera_utils import V4L2Camera, live_view

DEVICE = os.environ.get("DEVICE", "/dev/video0")
WIDTH = int(os.environ.get("WIDTH", "1920"))
HEIGHT = int(os.environ.get("HEIGHT", "1080"))
FPS = int(os.environ.get("FPS", "30"))


def main():
    cap = V4L2Camera(device=DEVICE, width=WIDTH, height=HEIGHT, fps=FPS)
    cap.open()
    if not cap.isOpened():
        print(f"Erreur: caméra inaccessible ({DEVICE}).", file=sys.stderr)
        sys.exit(1)

    live_view(cap, f"Viewer {DEVICE}  |  Q=quitter")


if __name__ == "__main__":
    main()
