.PHONY: replay-sequence build lock shell shell-robot up down teleop record replay-episode train train-sim eval push-checkpoint policy-server eval-remote setup-host setup-udev setup-oak check-devices calibrate-follower calibrate-leader scan-motors script-follower script-leader record-traj replay-traj detect-cameras detect-oak check-voltage check-voltage-follower check-voltage-leader check-oak photo

include mk/setup.mk
include mk/robot.mk
include mk/dataset.mk
include mk/camera.mk
