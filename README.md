# RobotKraft, version participants

> Ce dépôt est la base technique fournie aux équipes de RobotKraft 2026 : environnement Docker,
> pilotage des bras, enregistrement et rejeu de trajectoires, entraînement et évaluation de
> policies, outils de vision et de calibration.
>
> Il ne contient pas de solution aux épreuves : à vous de les écrire.
>
> Documentation de l'événement : https://docmost.alsacedigitale.org/share/yx3k53tasq/p/zCgLda8Z26

Robotique spatiale/chimie pour hackathon IA & Robotique : bras SO-ARM101 (leader/follower), imitation learning avec [LeRobot](https://huggingface.co/docs/lerobot), le tout conteneurisé sous Docker.

---

## Sécurité : ordre de branchement

**Branchement :**

1. Alimentation **d'abord** (7,4V nominal, servos STS3215 : vérifier le sticker OUTPUT avant de brancher)
2. Câble USB **follower**
3. Câble USB **leader**

**Pour débrancher, ordre inverse :** USB leader, USB follower puis enfin alimentation.

- Erreur `input voltage error` sous charge (~5,4V) : alimentation insuffisante.
- Ports `/dev/ttyACM0`/`ACM1` s'attribuent selon l'ordre de branchement (follower en premier = `ACM0`). Vérifier `ls /dev/ttyACM*` avant chaque session.

---

## Architecture

| Composant               |
|-------------------------|
| SO-ARM101               |
| LeRobot (HuggingFace)   |
| OAK-D Lite (depthai)    |
| Python 3.12.9 + uv      |
| Docker                  |

---

## Services Docker

| Service |
|---------|
| `lerobot-base` |
| `lerobot` |
| `lerobot-gpu` |
| `lerobot-follower` |
| `lerobot-leader` |
| `lerobot-camera` |

> `lerobot` requiert `/dev/lerobot_follower` **et** `/dev/lerobot_leader`. Un seul bras branché : `lerobot-follower` / `lerobot-leader` (montent `/dev/ttyACM0`/`ACM1`, sans symlink udev).

---

## Prérequis

- [Docker](https://www.docker.com/)
- `HF_TOKEN` dans `.env` (voir `.env.example`) pour push/pull datasets et checkpoints HuggingFace (obtenable via Access Token > Create New Token sur le site de HuggingFace)

---

## Installation

```bash
make build      # Build de l'image Docker
make setup-host # Groupe dialout (logout/login session juste après)
make setup-udev # Règles udev et symlinks pour le follower et leader (/dev/lerobot_follower + _leader)
make setup-oak  # Règle udev OAK-D Lite (une seule fois)
```

### Setup des servomoteurs

```bash
sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1
make setup-motors-follower  # Setup servomoteurs follower
make setup-motors-leader    # Setup servomoteurs leader
```

### Calibration des robots

```bash
make calibrate-follower # Calibration follower (une fois)
make calibrate-leader   # Calibration leader (une fois)
```

> Calibrations stockées dans `.cache/` (volume Docker). Pour recalibrer : supprimer le `.json` correspondant dans `.cache/huggingface/lerobot/calibration/`.

### Vérification après installation

```bash
ls /dev/ttyACM*    # follower/leader détectés
make check-devices # vérifie ACM0=follower, ACM1=leader
make check-voltage # tension de chaque servo (follower + leader)
```

### Caméra OAK-D Lite

- **USB3 obligatoire**
- `make setup-oak` une seule fois (règle udev + symlink `/dev/oak`)
- `make detect-oak` -> doit capturer un frame RGB pour valider la détection de la caméra
- **Ne jamais** `import depthai` depuis l'hôte, **ni** `docker run` (toujours `docker compose run lerobot-camera ...`) : un container éphémère peut garder le device verrouillé

---

## Features

Téléopération leader/follower, enregistrement de dataset pour l'imitation learning et replay de trajectoires uniques ou de séquences planifiées sur plusieurs mouvements.

Côté entraînement : policies ACT / SmolVLA / π0, sur GPU local ou distant. L'évaluation peut tourner en local (robot + policy sur la même machine) ou à distance, avec la policy via serveur d'inférence pendant que robot et caméra restent en local.

---

## Commandes

Toutes les commandes sont `make <cible>`. Le Makefile racine inclut `mk/{setup,robot,dataset,camera}.mk`, la cible se trouve dans le fichier correspondant à son domaine.

### Setup / image

| Commande | Description |
|----------|-------------|
| `make build` | Build l'image Docker `robokraft:latest` |
| `make shell` | Shell dans `lerobot-base` (sans robot) |
| `make lock` | Régénère `uv.lock` |
| `make setup-host` | Ajoute l'utilisateur au groupe `dialout` |
| `make setup-udev` | Crée `/dev/lerobot_follower` + `/dev/lerobot_leader` |
| `make setup-oak` | Crée la règle udev OAK-D Lite (`/dev/oak`) |

### Téléopération / calibration / diagnostic

| Commande | Description |
|----------|-------------|
| `make teleop` | Téléopération leader/follower en direct |
| `make setup-motors-follower` / `make setup-motors-leader` | Identification des servos d'un bras (une fois) |
| `make calibrate-follower` / `make calibrate-leader` | Calibration d'un bras (une fois) |
| `make check-devices` | Vérifie `ACM0`=follower, `ACM1`=leader |
| `make scan-motors` | Liste les IDs des servo-moteurs |
| `make check-voltage` | Tension des servos (follower + leader) |
| `make script-follower FILE=...` / `make script-leader FILE=...` | Lance un script Python avec accès direct à un seul bras |

### Enregistrement / replay

| Commande | Description |
|----------|-------------|
| `make record HF_USER=... TASK=...` | Enregistre un dataset de téléopération (`[NUM_EPISODES]`, `[EPISODE_TIME]`, `[RESET_TIME]`, `[RESUME]`) |
| `make replay-episode HF_USER=... TASK=... [EPISODE=0]` | Rejoue un épisode d'un dataset enregistré (follower seul) |

### Entraînement / évaluation

| Commande | Description |
|----------|-------------|
| `make train HF_USER=... TASK=...` | Entraîne une policy ACT (GPU local) |
| `make eval TASK=... [HF_USER=...] [CHECKPOINT=last]` | Évalue une policy sur le robot réel, inférence locale |
| `make push-checkpoint HF_USER=... TASK=...` | Push un checkpoint entraîné sur HF Hub (requis avant `eval-remote`) |
| `make policy-server` | Lance le serveur d'inférence en local |
| `make eval-remote HF_USER=... TASK=... SERVER=ip:port` | Évalue avec policy sur GPU distant, robot + caméra en local |

### Vision / caméra

| Commande | Description |
|----------|-------------|
| `make detect-oak` / `make detect-cameras` | Détection caméra OAK-D Lite / caméras disponibles |
| `make calibrate-wb` | Calibration de la balance des blancs |
| `make view-camera DEVICE=/dev/video2` | Preview live webcam USB générique (ET-231 et similaires), exécuté sur l'hôte |
| `make photo [FILE=...] [CROP_X/Y/W/H=...]` | Capture une photo |

