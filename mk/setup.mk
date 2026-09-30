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
