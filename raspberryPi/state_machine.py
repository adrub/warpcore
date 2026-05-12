# state_machine.py

from config import VALID_RACE_STATES


class RaceStateMachine:
    def __init__(self, led_controller=None):
        self.current_state = "idle"
        self.led_controller = led_controller

    def set_state(self, new_state):
        if new_state not in VALID_RACE_STATES:
            print(f"[STATE MACHINE] Invalid state received: {new_state}")
            return

        previous_state = self.current_state
        self.current_state = new_state

        print(f"[STATE MACHINE] {previous_state} -> {new_state}")

        self._handle_state_change(new_state)

    def _handle_state_change(self, state):
        if state == "idle":
            print("[ACTION] Idle mode")
            self._set_led_effect("slow_pulse")

        elif state == "ready":
            print("[ACTION] Ready mode")
            self._set_led_effect("steady_glow")

        elif state == "countdown":
            print("[ACTION] Countdown mode")
            self._set_led_effect("countdown_flash")

        elif state == "racing":
            print("[ACTION] Racing mode")
            self._set_led_effect("warp_animation")

        elif state == "finished":
            print("[ACTION] Finished mode")
            self._set_led_effect("celebration_flash")

        elif state == "error":
            print("[ACTION] Error mode")
            self._set_led_effect("error_flash")

    def _set_led_effect(self, effect_name):
        if self.led_controller is None:
            print(f"[LED PLACEHOLDER] Effect: {effect_name}")
        else:
            self.led_controller.set_effect(effect_name)