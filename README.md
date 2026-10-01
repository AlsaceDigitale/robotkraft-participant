# RobotKraft, version participants

> Base technique fournie aux équipes de RobotKraft 2026 : environnement Docker prêt à l'emploi,
> détection des bras et des caméras, diagnostic matériel, et raccourcis vers les commandes
> LeRobot (téléopération, enregistrement de datasets, entraînement, évaluation en local ou sur
> GPU distant).
>
> La perception et la stratégie ne sont pas fournies : c'est ce que le challenge évalue, à vous
> de l'écrire.
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

L'image est prete, il n'y a rien a compiler. Tire-la plutot que de la construire, tu gagnes
une vingtaine de minutes et tu economises la connexion du lieu :

```bash
docker compose pull      # recupere l'image depuis ghcr.io
```

**Fais-le chez toi avant de venir.** L'image pese environ 2,7 Go, et cinquante
telechargements simultanes sur la connexion du lieu, le vendredi soir, ce n'est
pas une bonne soiree.

Si ton portable a un GPU NVIDIA et que tu veux entrainer en local, bascule sur la
variante CUDA (environ 9 Go) :

```bash
make use-cuda            # ecrit le choix dans .env, donc il persiste
docker compose pull
make which-image         # verifie : doit afficher GPU vu par torch : True
```

Sinon, l'entrainement se fait sur les serveurs GPU distants, et la variante par
defaut suffit. `make use-cpu` revient en arriere.

⚠️ Ne passe pas `ROBOKRAFT_IMAGE=...` directement devant une commande : la valeur
ne vaut que pour cette commande, et `make train` repartirait sur la variante CPU
en entrainant sur processeur sans rien signaler.

### Regler ta machine, obligatoire meme si tu tires l'image

Ces trois commandes configurent ton systeme, pas l'image. Sans elles, les bras et
la camera ne seront pas visibles depuis les conteneurs.

```bash
make setup-host # Groupe dialout (deconnecte puis reconnecte ta session juste apres)
make setup-udev # Regles udev et symlinks /dev/lerobot_follower et _leader
make setup-oak  # Regle udev pour la camera OAK-D Lite (une seule fois)
```

Copie aussi le fichier de configuration :

```bash
cp .env.example .env    # puis renseigne HF_TOKEN
```

### Reconstruire l'image, seulement si tu modifies le Dockerfile ou les dependances

```bash
make build
```

### ⛔ Ne reconfigure pas les servomoteurs

Les identifiants des servos sont **deja definis sur les bras qu'on te prete**, et
toute la chaine en depend. Les redefinir casse le bras pour toi et pour l'equipe
qui l'utilisera apres toi, et il faut ensuite le reconfigurer servo par servo.

**Ne lance jamais `lerobot-setup-motors`, ni aucune commande de configuration des
identifiants moteurs.** Si un servo semble muet ou mal numerote, ce n'est pas a toi
de le reparer : viens voir un coach.

Pour verifier que les servos repondent, sans rien modifier :

```bash
make scan-motors    # liste les identifiants vus sur le bus
make check-voltage  # tension de chaque servo
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

Téléopération leader/follower, enregistrement de datasets pour l'apprentissage par imitation, et rejeu d'un épisode enregistré.

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
| `make calibrate-follower` / `make calibrate-leader` | Calibration d'un bras (une fois) |
| `make check-devices` | Vérifie `ACM0`=follower, `ACM1`=leader |
| `make scan-motors` | Liste les IDs des servo-moteurs |
| `make check-voltage` | Tension des servos (follower + leader) |
| `make check-voltage-follower` / `make check-voltage-leader` | Tension d'un seul bras |
| `make check-oak` | Verifie que la camera OAK-D est bien detectee par l'hote |
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

---

## Bloque ? Ou demander de l'aide

- **Pendant l'evenement** : le salon `support-technique` du Discord, ou un coach dans la salle.
- **Discord** : https://discord.gg/njTBunuwUA
- **Documentation de l'evenement** : lieu, horaires, repas, reglement, epreuves.
  https://docmost.alsacedigitale.org/share/7znmwljzor/p/REgtr0f3SX
