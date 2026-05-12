# main.py

import time

from state_machine import RaceStateMachine
from telemetry import TelemetryHandler
from mqtt_client import PiMQTTClient
from control_publisher import ControlPublisher
from hardware.led_controller import LEDController
from hardware.button_controller import ButtonController


def main():
    print("[SYSTEM] Starting Warp-Core Pi controller")

    led_controller = LEDController()
    state_machine = RaceStateMachine(led_controller=led_controller)
    telemetry_handler = TelemetryHandler()

    mqtt_client = PiMQTTClient(
        state_machine=state_machine,
        telemetry_handler=telemetry_handler
    )

    control_publisher = ControlPublisher(mqtt_client)

    button_controller = ButtonController(
        control_callback=control_publisher.send_command
    )

    mqtt_client.connect()

    print("[SYSTEM] Pi controller running")
    print("[SYSTEM] Commands for manual testing:")
    print("  start  - publish start command to PC")
    print("  reset  - publish reset command to PC")
    print("  idle   - publish idle command to PC")
    print("  state  - show current race state")
    print("  quit   - exit")

    try:
        while True:
            command = input("> ").strip().lower()

            if command == "quit":
                break

            elif command in {"start", "reset", "idle"}:
                button_controller.simulate_button_press(command)

            elif command == "state":
                print(f"[SYSTEM] Current state: {state_machine.current_state}")

            else:
                print("[SYSTEM] Unknown command")

    except KeyboardInterrupt:
        print("\n[SYSTEM] Keyboard interrupt received")

    finally:
        mqtt_client.disconnect()
        print("[SYSTEM] Pi controller stopped")


if __name__ == "__main__":
    main()