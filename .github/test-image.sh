#!/usr/bin/env bash
# Verifie qu'une image robokraft est utilisable : dependances importables,
# entrees LeRobot presentes, scripts compilables, et aucune solution d'epreuve.
# Usage : .github/test-image.sh <reference-image>
set -euo pipefail
IMG="${1:?usage: test-image.sh <image>}"
run() { docker run --rm "$IMG" "$@"; }

echo "-- les dependances s'importent"
run python3 -c '
import torch, cv2, zmq, transformers, lerobot, depthai
print("  torch       ", torch.__version__)
print("  opencv      ", cv2.__version__)
print("  transformers", transformers.__version__)
print("  lerobot     ", lerobot.__version__)
print("  pyzmq       ", zmq.__version__)
print("  depthai     ", depthai.__version__)
'

echo "-- les entrees LeRobot utilisees par le Makefile existent"
run python3 -c '
import importlib
for m in ["lerobot.scripts.lerobot_record", "lerobot.scripts.lerobot_train",
          "lerobot.scripts.lerobot_eval", "lerobot.scripts.lerobot_teleoperate",
          "lerobot.scripts.lerobot_calibrate", "lerobot.scripts.lerobot_setup_motors"]:
    importlib.import_module(m)
    print("  ", m.rsplit(".", 1)[1])
'

echo "-- tous les scripts du depot compilent"
run python3 -m compileall -q scripts/
echo "  scripts/ : OK"

echo "-- aucune solution d'epreuve dans l'image"
if run sh -c 'test -d scripts/tasks'; then
  echo "  ECHEC : scripts/tasks present dans l'image" >&2
  exit 1
fi
echo "  scripts/tasks absent : OK"

echo "-- torch fonctionne reellement (petit calcul)"
run python3 -c '
import torch
a = torch.ones(64, 64)
assert torch.allclose(a @ a, torch.full((64, 64), 64.0)), "produit matriciel faux"
print("  produit matriciel : OK")
'
echo
echo "image utilisable."
