import time
from mqtt_client import WarpCoreMQTTClient
from race_controller import RaceController


def main():
    mqtt_client = WarpCoreMQTTClient(
        broker_ip="172.20.10.4",
        port=1883
    )

    race_controller = RaceController(mqtt_client)

    mqtt_client.set_command_callback(race_controller.handle_pi_command)
    mqtt_client.connect()

    race_controller.set_state("idle")

    print("PC race wrapper running.")
    print("Commands:")
    print("  start  - simulate race start")
    print("  reset  - reset to idle")
    print("  finish - finish race")
    print("  telem  - send fake telemetry")
    print("  quit   - exit")

    try:
        while True:
            command = input("> ").strip().lower()

            if command == "start":
                race_controller.start_race()
            elif command == "reset":
                race_controller.reset_race()
            elif command == "finish":
                race_controller.finish_race()
            elif command == "telem":
                race_controller.send_fake_telemetry()
            elif command == "quit":
                break
            else:
                print("Unknown command.")

    finally:
        race_controller.set_state("idle")
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()