# hardware/button_controller.py


class ButtonController:
    def __init__(self, control_callback=None):
        self.control_callback = control_callback
        print("[BUTTON] Button controller initialized")
        print("[BUTTON] No physical button hardware connected yet")

    def simulate_button_press(self, command):
        if self.control_callback:
            self.control_callback(command)