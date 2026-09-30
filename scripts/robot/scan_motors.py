"""Scanne les IDs moteurs présents sur chaque port série"""

from lerobot.motors.feetech import FeetechMotorsBus

for port, name in [("/dev/ttyACM0", "follower"), ("/dev/ttyACM1", "leader")]:
    print(f"\n=== {port} ({name}) ===")
    try:
        result = FeetechMotorsBus.scan_port(port)
        print("scan_port:", result)
    except Exception as e:
        print("scan_port error:", e)
    bus = FeetechMotorsBus(port=port, motors={})
    bus.connect(handshake=False)
    try:
        ids = bus.broadcast_ping()
        print("broadcast_ping:", ids)
    except Exception as e:
        print("broadcast_ping error:", e)
    bus.disconnect()
