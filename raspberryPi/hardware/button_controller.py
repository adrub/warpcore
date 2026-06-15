# hardware/button_controller.py

import RPi.GPIO as GPIO

from config import (
    BUTTON_PIN_START,
    BUTTON_PIN_RESET,
    BUTTON_DEBOUNCE_MS,
)


class ButtonController:
    def __init__(self, control_publisher=None, control_callback=None):
        self.control_publisher = control_publisher
        self.control_callback = control_callback

        self._buttons = {
            BUTTON_PIN_START: "start",
            BUTTON_PIN_RESET: "reset",
        }

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in self._buttons:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                pin,
                GPIO.FALLING,           # FALLING = button pressed (pin pulled low)
                callback=self._on_press,
                bouncetime=BUTTON_DEBOUNCE_MS,
            )

        print("[BUTTON] Seimitsu PS-14-K buttons initialised")
        print(f"  START → GPIO {BUTTON_PIN_START}")
        print(f"  RESET → GPIO {BUTTON_PIN_RESET}")

    def _on_press(self, pin):
        command = self._buttons.get(pin)
        if command is None:
            print(f"[BUTTON] Press on unknown pin {pin}")
            return

        print(f"[BUTTON] Pressed: {command} (GPIO {pin})")

        self._send_control_command(command)

    def simulate_button_press(self, command):
        """For manual testing via the terminal input loop."""
        print(f"[BUTTON] Simulated press: {command}")
        self._send_control_command(command)

    def _send_control_command(self, command):
        if self.control_publisher:
            self.control_publisher.send_command(command)
            return

        if self.control_callback:
            self.control_callback(command)

    def cleanup(self):
        """Call this on shutdown to release GPIO resources."""
        GPIO.cleanup()
        print("[BUTTON] GPIO cleaned up")
