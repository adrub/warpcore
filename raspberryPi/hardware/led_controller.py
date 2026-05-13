# hardware/led_controller.py

import time
import threading
import math

from rpi_ws281x import PixelStrip, Color

from config import (
    LED_COUNT,
    LED_PIN,
    LED_FREQ_HZ,
    LED_DMA,
    LED_BRIGHTNESS,
    LED_INVERT,
    LED_CHANNEL,
)

OFF        = Color(0,   0,   0)
BLUE       = Color(0,   0,   255)
CYAN       = Color(0,   200, 255)
WHITE      = Color(255, 255, 255)
COLD_WHITE = Color(180, 210, 255) 
RED        = Color(255, 0,   0)
ORANGE     = Color(255, 80,  0)
GREEN      = Color(0,   255, 0)
PURPLE     = Color(180, 0,   255)


class LEDController:
    def __init__(self):
        self.strip = PixelStrip(
            LED_COUNT,
            LED_PIN,
            LED_FREQ_HZ,
            LED_DMA,
            LED_INVERT,
            LED_BRIGHTNESS,
            LED_CHANNEL,
        )
        self.strip.begin()
        self._stop_event = threading.Event()
        self._thread = None

        self._fill(OFF)
        print("[LED] WS2812B strip initialised")

    def set_effect(self, effect_name: str):
        """Stop any running effect and start a new one."""
        self._stop_current()

        effects = {
            "slow_pulse":       self._effect_slow_pulse,
            "steady_glow":      self._effect_steady_glow,
            "countdown_flash":  self._effect_countdown_flash,
            "warp_animation":   self._effect_warp_animation,
            "celebration_flash":self._effect_celebration_flash,
            "error_flash":      self._effect_error_flash,
        }

        fn = effects.get(effect_name)
        if fn is None:
            print(f"[LED] Unknown effect: {effect_name}")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=fn, daemon=True)
        self._thread.start()
        print(f"[LED] Effect started: {effect_name}")

    def clear(self):
        self._stop_current()
        self._fill(OFF)


    def _effect_slow_pulse(self):
        while not self._stop_event.is_set():
            for step in range(0, 628):      
                if self._stop_event.is_set():
                    return
                brightness = (math.sin(step / 100.0) + 1) / 2 
                r = int(0   * brightness)
                g = int(180 * brightness)
                b = int(255 * brightness)
                self._fill(Color(r, g, b))
                time.sleep(0.01)              

    def _effect_steady_glow(self):
        self._fill(COLD_WHITE)
        self._stop_event.wait()       

    def _effect_countdown_flash(self):
        delays = [0.6, 0.45, 0.3]         
        for delay in delays:
            if self._stop_event.is_set():
                return
            self._fill(BLUE)
            time.sleep(0.15)
            self._fill(OFF)
            time.sleep(delay)

        if not self._stop_event.is_set():
            self._fill(WHITE)
            time.sleep(0.3)
            self._fill(OFF)

    def _effect_warp_animation(self):
        tail_length = max(4, LED_COUNT // 6)

        position = 0
        while not self._stop_event.is_set():
            self._fill(OFF)

            for t in range(tail_length):
                pixel = (position - t) % LED_COUNT
                fade  = 1.0 - (t / tail_length)  
                r = int(180 * fade)
                g = int(240 * fade)
                b = int(255 * fade)
                self.strip.setPixelColor(pixel, Color(r, g, b))

            self.strip.show()
            position = (position + 1) % LED_COUNT
            time.sleep(0.025)     

    def _effect_celebration_flash(self):
        colours = [CYAN, WHITE, PURPLE, BLUE, GREEN, ORANGE, WHITE, CYAN]
        for _ in range(4):                    
            for colour in colours:
                if self._stop_event.is_set():
                    return
                self._fill(colour)
                time.sleep(0.12)
                self._fill(OFF)
                time.sleep(0.06)

        if not self._stop_event.is_set():
            self._fill(CYAN)
            self._stop_event.wait()

    def _effect_error_flash(self):
        while not self._stop_event.is_set():
            for _ in range(2):                   
                if self._stop_event.is_set():
                    return
                self._fill(RED)
                time.sleep(0.1)
                self._fill(OFF)
                time.sleep(0.1)
            time.sleep(0.6)                    

    def _fill(self, colour: Color):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, colour)
        self.strip.show()

    def _stop_current(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)
        self._thread = None