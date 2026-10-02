"""Preview live de l'OAK-D Lite via le flux ZMQ de oak_zmq_server.py. Affiche résolution/fps réel à l'écran.
Nécessite oak_zmq_server.py lancé en parallèle (voir scripts/shell/calibrate_with_oak.sh pour le pattern)."""

import sys
import time

import cv2

from camera_utils import ZMQCamera


def main():
    """Boucle d'affichage. Q/Echap pour quitter"""
    cap = ZMQCamera()
    cap.open()
    if not cap.isOpened():
        print("Erreur: OAK-D Lite inaccessible via ZMQ (oak_zmq_server.py est-il lancé ?).", file=sys.stderr)
        sys.exit(1)

    win = "Viewer OAK-D Lite  |  Q=quitter"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 1280, 720)

    n = 0
    t_fps = time.time()
    fps_disp = 0.0
    consecutive_misses = 0
    # 15 lectures ratées d'affilée (~30s à 2s/lecture) : couvre le warm-up du serveur
    # (10 frames jetées avant publication) même à FPS bas, pas juste une vraie coupure.
    MAX_CONSECUTIVE_MISSES = 15

    while True:
        ret, frame = cap.read()
        if not ret:
            consecutive_misses += 1
            if consecutive_misses >= MAX_CONSECUTIVE_MISSES:
                print("Erreur: frame vide (flux ZMQ coupé ?)", file=sys.stderr)
                break
            continue
        consecutive_misses = 0

        n += 1
        elapsed = time.time() - t_fps
        if elapsed >= 1.0:
            fps_disp = n / elapsed
            n = 0
            t_fps = time.time()

        h, w = frame.shape[:2]
        info = f"{w}x{h}  {fps_disp:.1f} fps  (Q=quitter)"
        cv2.putText(frame, info, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.imshow(win, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
