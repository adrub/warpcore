# hardware/led_controller.py


class LEDController:
    def __init__(self):
        print("[LED] LED controller initialized")
        print("[LED] No physical LED hardware connected yet")

    def set_effect(self, effect_name):
        print(f"[LED] Future LED effect selected: {effect_name}")