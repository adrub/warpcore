# hardware/button_controller.py

import threading
import time

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
        self._use_polling = False
        self._last_states = {}
        self._poll_stop_event = threading.Event()
        self._poll_thread = None
        self._last_press_time = {}

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in self._buttons:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._last_states[pin] = GPIO.input(pin)
            self._last_press_time[pin] = 0

            try:
                GPIO.add_event_detect(
                    pin,
                    GPIO.FALLING,
                    callback=self._on_press,
                    bouncetime=BUTTON_DEBOUNCE_MS,
                )
            except RuntimeError as exc:
                print(f"[BUTTON] Warning: could not add event detection for GPIO {pin}: {exc}")
                self._use_polling = True

        if self._use_polling:
            self._poll_thread = threading.Thread(target=self._poll_buttons_loop, daemon=True)
            self._poll_thread.start()

        print("[BUTTON] Seimitsu PS-14-K buttons initialised")
        print(f"  START → GPIO {BUTTON_PIN_START}")
        print(f"  RESET → GPIO {BUTTON_PIN_RESET}")

    def _on_press(self, pin):
        now = time.monotonic() * 1000
        last_press = self._last_press_time.get(pin, 0)
        if now - last_press < BUTTON_DEBOUNCE_MS:
            return

        self._last_press_time[pin] = now
        command = self._buttons.get(pin)
        if command is None:
            print(f"[BUTTON] Press on unknown pin {pin}")
            return

        print(f"[BUTTON] Pressed: {command} (GPIO {pin})")
        self._send_control_command(command)

    def _poll_buttons_loop(self):
        while not self._poll_stop_event.is_set():
            for pin, command in self._buttons.items():
                state = GPIO.input(pin)
                last_state = self._last_states.get(pin, GPIO.HIGH)

                if last_state == GPIO.HIGH and state == GPIO.LOW:
                    self._on_press(pin)

                self._last_states[pin] = state

            time.sleep(0.02)

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
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_stop_event.set()
            self._poll_thread.join(timeout=1.0)

        for pin in self._buttons:
            try:
                GPIO.remove_event_detect(pin)
            except RuntimeError:
                pass

        GPIO.cleanup()
        print("[BUTTON] GPIO cleaned up")
