#!/usr/bin/env bash
# Verifie qu'une image robokraft est utilisable : dependances importables,
# entrees LeRobot presentes, scripts compilables, et aucune solution d'epreuve.
# Usage : .github/test-image.sh <reference-image> [cpu|cuda]
set -euo pipefail
IMG="${1:?usage: test-image.sh <image> [variante]}"
VARIANTE="${2:-}"
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

echo "-- torch et torchvision sont compatibles"
# Un torchvision compile pour CUDA face a un torch CPU passe l'import sans
# broncher et casse au premier appel d'operateur natif. On appelle donc nms.
run python3 -c '
import torch, torchvision
from torchvision.ops import nms
boites = torch.tensor([[0., 0., 10., 10.], [1., 1., 11., 11.]])
scores = torch.tensor([0.9, 0.8])
assert nms(boites, scores, 0.5).numel() >= 1
print("  torch", torch.__version__, "/ torchvision", torchvision.__version__, ": operateurs natifs OK")
'

echo "-- torch fonctionne reellement (petit calcul)"
run python3 -c '
import torch
a = torch.ones(64, 64)
assert torch.allclose(a @ a, torch.full((64, 64), 64.0)), "produit matriciel faux"
print("  produit matriciel : OK")
'
if [ -n "$VARIANTE" ]; then
  echo "-- la variante $VARIANTE contient ce qu'elle annonce"
  v=$(run python3 -c 'import torch; print(torch.__version__)')
  echo "    torch : $v"
  n=$(run sh -c 'ls .venv/lib/python3.12/site-packages 2>/dev/null | grep -ci "^nvidia\|^triton" || true')
  echo "    paquets nvidia/triton : $n"
  case "$VARIANTE" in
    cpu)
      case "$v" in *+cu*) echo "  ECHEC : torch CUDA dans la variante cpu" >&2; exit 1;; esac
      [ "$n" -gt 0 ] && { echo "  ECHEC : $n paquets nvidia dans la variante cpu" >&2; exit 1; }
      echo "    variante cpu : OK" ;;
    cuda)
      case "$v" in *+cu*) : ;; *) echo "  ECHEC : torch sans CUDA dans la variante cuda" >&2; exit 1;; esac
      [ "$n" -eq 0 ] && { echo "  ECHEC : aucun paquet nvidia dans la variante cuda" >&2; exit 1; }
      echo "    variante cuda : OK" ;;
  esac
fi

echo
echo "image utilisable."
