#TORCS control and automation functions

import subprocess
import time
import xml.etree.ElementTree as ET

from . import state
from .config import QUICKRACE_XML

# Assigns sequential UDP ports starting at 3001 to each car in the race config
def assign_ports():
    for i, car in enumerate(state.race_config):
        car["port"] = 3001 + i

# Rewrites TORCS's quickrace.xml to match the current number of cars before each race
def patch_quickrace_xml(n_cars):
    tree = ET.parse(QUICKRACE_XML)
    root = tree.getroot()
    for section in root.findall("section"):
        if section.get("name") in ("Drivers", "Drivers Start List"):
            root.remove(section)

    drivers_el = ET.SubElement(root, "section")
    drivers_el.set("name", "Drivers")
    for attr, val in [("maximum number", "40"), ("focused idx", "0")]:
        e = ET.SubElement(drivers_el, "attnum")
        e.set("name", attr); e.set("val", val)
    fm = ET.SubElement(drivers_el, "attstr")
    fm.set("name", "focused module"); fm.set("val", "scr_server")
    for i in range(n_cars):
        s = ET.SubElement(drivers_el, "section"); s.set("name", str(i + 1))
        a = ET.SubElement(s, "attnum"); a.set("name", "idx"); a.set("val", str(i))
        b = ET.SubElement(s, "attstr"); b.set("name", "module"); b.set("val", "scr_server")

    sl = ET.SubElement(root, "section"); sl.set("name", "Drivers Start List")
    for i in range(n_cars):
        s = ET.SubElement(sl, "section"); s.set("name", str(i + 1))
        a = ET.SubElement(s, "attstr"); a.set("name", "module"); a.set("val", "scr_server")
        b = ET.SubElement(s, "attnum"); b.set("name", "idx"); b.set("val", str(i))

    ET.indent(tree, space="  ")
    tree.write(QUICKRACE_XML, xml_declaration=True, encoding="UTF-8")

# Navigates the TORCS exit menu using simulated keypresses 
def _xdotool(*args):
    r = subprocess.run(["xdotool", *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()

# Navigates the TORCS exit menu using simulated keypresses - no quit API exists
def quit_torcs():
    code, out = _xdotool("search", "--name", "torcs")
    if code != 0 or not out:
        return
    wid = out.splitlines()[0]
    _xdotool("windowfocus", "--sync", wid)
    time.sleep(0.2)
    for key, delay in [
        ("Escape", 0.8),
        ("Down", 0.2), ("Down", 0.2), ("Down", 0.2),
        ("Return", 0.8),
        ("Down", 0.2),
        ("Return", 1.0),
    ]:
        _xdotool("key", "--window", wid, key)
        time.sleep(delay)

# Waits for the TORCS window to appear then presses through the menus to start the race
def autostart_torcs():
    print("[autostart] Waiting for TORCS window...")
    wid = None
    for _ in range(30):
        code, out = _xdotool("search", "--name", "torcs")
        if code == 0 and out:
            wid = out.splitlines()[0]
            break
        time.sleep(0.5)
    if not wid:
        print("[autostart] TORCS window not found - start race manually")
        return
    print(f"[autostart] Found window {wid}, navigating menu...")
    time.sleep(2.0)
    _xdotool("windowfocus", "--sync", wid)
    time.sleep(0.3)
    for key, delay in [("Return", 1.0), ("Return", 1.0), ("Return", 1.0), ("Return", 0.5)]:
        _xdotool("key", "--window", wid, key)
        time.sleep(delay)
    print("[autostart] Race started.")
