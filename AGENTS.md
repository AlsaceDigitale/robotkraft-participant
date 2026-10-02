# Pour l'agent qui travaille dans ce dépôt

Ce dépôt pilote du matériel physique réel : bras robotiques SO-ARM101 (servomoteurs
STS3215) et caméras (OAK-D Lite, webcam USB). Les scripts qu'on lance ici ne sont pas de
simples tests logiciels — ils peuvent déplacer un bras, couper son maintien de position,
ou verrouiller une caméra pour un autre process. Quelques réflexes avant d'exécuter quoi
que ce soit qui touche au matériel :

## Bras robotiques

- **Un script qui bouge le bras le bouge vraiment.** `lerobot-teleoperate`,
  `lerobot-calibrate`, `move_central_position.py` et tout ce qui écrit `Goal_Position`
  déplace un servomoteur réel. Avant de lancer une de ces commandes, savoir ce qu'il y a
  autour du bras (câbles, mains, objets fragiles), et rester présent la première fois.
- **Ne jamais lancer `lerobot-setup-motors` ni aucune commande de configuration
  d'identifiants moteurs.** Les IDs sont déjà réglés sur les bras prêtés ; les redéfinir
  casse le bras pour l'équipe suivante, qui doit ensuite le reconfigurer servo par servo.
  Si un servo semble muet ou mal numéroté, ce n'est pas à corriger seul — remonter le
  problème plutôt que d'improviser une commande de configuration.
- **Ordre de branchement : alimentation d'abord, USB ensuite.** Dans l'autre sens, le
  port USB alimente la carte et peut la griller. Débranchement : ordre inverse (voir
  README, section Sécurité).
- **Ne pas déduire follower/leader du port ou de l'ordre de branchement.**
  `/dev/ttyACM0`/`ACM1` (ou `/dev/cu.usbmodem*` sous macOS) ne garantissent rien : l'ordre
  dépend du branchement physique, pas d'une convention fixe — vérifié en pratique, les
  deux bras partagent le même VID:PID USB. `scripts/robot/identify_arms.py` identifie le
  rôle réel par la tension mesurée (follower ~12V, leader ~5V) : s'en servir en cas de
  doute plutôt que de supposer. `check_devices.py`/`scan_motors.py` ne vérifient qu'une
  connexion, pas le rôle : leur étiquette "follower"/"leader" peut être fausse.
- **`bus.disconnect()` coupe le maintien de position par défaut.** Un script qui ne fait
  que lire une valeur (tension, scan de moteurs) sans vouloir relâcher le bras doit passer
  `disable_torque=False` explicitement — sinon le bras tombe en mou à la fin du script,
  même en pleine session active.

## Caméras

- **Ne jamais ouvrir l'OAK-D Lite depuis deux process à la fois.** `depthai` verrouille
  le device ; un process resté ouvert (y compris un container Docker éphémère non
  nettoyé) empêche tout autre accès tant qu'il n'est pas fermé proprement.
- Avant de conclure qu'une caméra est en panne, vérifier qu'aucun autre process ne la
  tient déjà, et qu'elle est bien branchée — un comportement bizarre (boot qui échoue,
  device introuvable) est aussi souvent un câble débranché qu'un vrai bug.

## En cas de doute

Un comportement matériel surprenant (bras qui ne répond pas, tension anormale, caméra
inaccessible) mérite d'être vérifié avant d'être corrigé. Ce n'est pas forcément un bug
du code : ça peut être le matériel lui-même (branchement, alimentation, bras déjà
verrouillé par un autre process, device physiquement débranché).
