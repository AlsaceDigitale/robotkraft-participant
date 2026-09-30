setup-host:
	sudo usermod -aG dialout $(USER)
	@echo "Déconnectez-vous et reconnectez-vous pour appliquer le groupe dialout."

# Crée /dev/lerobot_follower et /dev/lerobot_leader (règles udev stables).
# À lancer une seule fois, avec les deux bras disponibles.
setup-udev:
	bash scripts/shell/setup_udev.sh

# Crée règle udev pour OAK-D Lite (Luxonis/Movidius 03e7) + symlink /dev/oak. À lancer une seule fois.
setup-oak:
	echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666", SYMLINK+="oak"' \
		| sudo tee /etc/udev/rules.d/80-movidius.rules
	sudo udevadm control --reload-rules && sudo udevadm trigger
	@echo "Débrancher/rebrancher l'OAK-D Lite puis vérifier : ls -la /dev/oak"

check-oak:
	@test -e /dev/oak || (echo "Erreur: OAK-D Lite non détecté (/dev/oak absent). Brancher et relancer (make setup-oak si première fois)." && exit 1)
	@echo "OAK-D Lite détecté OK"

build:
	docker compose build lerobot

lock:
	docker run --rm -v "$$(pwd):/workspace/hostrepo" -w /workspace/hostrepo robokraft:latest uv lock

up:
	docker compose up -d lerobot

down:
	docker compose down

shell:
	docker compose run --rm lerobot-base

# Shell avec accès aux deux bras (/dev/ttyACM0, /dev/ttyACM1 via symlinks udev)
shell-robot:
	docker compose run --rm lerobot bash

# Bascule la variante d'image utilisee par toutes les commandes, en ecrivant
# dans .env. Sans ca, une valeur passee en ligne de commande ne vaut que pour
# la commande en cours.
use-cuda:
	@touch .env && sed -i.bak '/^ROBOKRAFT_IMAGE=/d' .env && rm -f .env.bak
	@echo 'ROBOKRAFT_IMAGE=ghcr.io/alsacedigitale/robokraft:cuda' >> .env
	@echo "Variante CUDA selectionnee. Lance : docker compose pull"

use-cpu:
	@touch .env && sed -i.bak '/^ROBOKRAFT_IMAGE=/d' .env && rm -f .env.bak
	@echo "Variante CPU selectionnee (defaut). Lance : docker compose pull"

# Dit quelle variante est reellement active et si torch voit un GPU
which-image:
	@echo "image : $${ROBOKRAFT_IMAGE:-$$(grep -E '^ROBOKRAFT_IMAGE=' .env 2>/dev/null | cut -d= -f2- || echo 'ghcr.io/alsacedigitale/robokraft:latest (defaut)')}"
	@docker compose run --rm lerobot-base python3 -c "import torch; print('torch :', torch.__version__); print('GPU vu par torch :', torch.cuda.is_available())" 2>/dev/null || echo "(image non tiree)"
