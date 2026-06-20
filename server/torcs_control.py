#TORCS control and automation functions

import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

from . import state
from .config import QUICKRACE_XML, RACE_LAPS

SCR_SERVER_XML_SRC = "/usr/local/share/games/torcs/drivers/scr_server/scr_server.xml"
SCR_SERVER_XML_DST = os.path.expanduser("~/.torcs/drivers/scr_server/scr_server.xml")
TORCS_CARS_DIR     = "/usr/local/share/games/torcs/cars"

# Assigns sequential UDP ports starting at 3001 to each car in the race config
def assign_ports():
    for i, car in enumerate(state.race_config):
        car["port"] = 3001 + i

# Rewrites TORCS's quickrace.xml to match the current number of cars before each race
def patch_quickrace_xml(n_cars):
    tree = ET.parse(QUICKRACE_XML)
    root = tree.getroot()
    # Set the race length so TORCS ends where the finish monitor watches for it.
    for section in root.findall("section"):
        if section.get("name") == "Quick Race":
            for attnum in section.findall("attnum"):
                if attnum.get("name") == "laps":
                    attnum.set("val", str(RACE_LAPS))
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


# Creates a per-slot car model directory with a recoloured texture derived from car1-ow1
def _make_slot_car(slot_idx, hex_color):
    from PIL import Image
    car_name = f"warpcore-c{slot_idx}"
    slot_dir = os.path.join(TORCS_CARS_DIR, car_name)
    os.makedirs(slot_dir, exist_ok=True)
    src_dir = os.path.join(TORCS_CARS_DIR, "car1-ow1")

    hx = hex_color.lstrip("#")
    tr, tg, tb = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    mx = max(tr, tg, tb, 1)

    # Remap the car body: source R channel drives intensity, target colour sets hue
    img = Image.open(os.path.join(src_dir, "car1-ow1.rgb")).convert("RGBA")
    r, g, b, a = img.split()
    new_r = r.point(lambda x: x * tr // mx)
    new_g = r.point(lambda x: x * tg // mx)
    new_b = r.point(lambda x: x * tb // mx)
    Image.merge("RGBA", (new_r, new_g, new_b, a)).save(
        os.path.join(slot_dir, f"{car_name}.rgb"), format="SGI"
    )

    # Copy static assets that don't need recolouring
    for fname in ("shadow.rgb", "tex-wheel.rgb"):
        shutil.copy2(os.path.join(src_dir, fname), os.path.join(slot_dir, fname))

    # Patch .acc to reference the new texture name
    with open(os.path.join(src_dir, "car1-ow1.acc")) as f:
        acc = f.read()
    with open(os.path.join(slot_dir, f"{car_name}.acc"), "w") as f:
        f.write(acc.replace("car1-ow1.rgb", f"{car_name}.rgb"))

    # Patch car XML: rename params block and .acc reference
    with open(os.path.join(src_dir, "car1-ow1.xml")) as f:
        xml = f.read()
    xml = xml.replace('name="car1-ow1" type=', f'name="{car_name}" type=')
    xml = xml.replace('"car1-ow1.acc"', f'"{car_name}.acc"')
    with open(os.path.join(slot_dir, f"{car_name}.xml"), "w") as f:
        f.write(xml)

    return car_name


# Generates per-slot coloured car models and writes a patched scr_server.xml
def patch_car_colours(race_config):
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("[colors] Pillow not installed — run: pip install Pillow")
        return

    tree = ET.parse(SCR_SERVER_XML_SRC)
    root = tree.getroot()
    for robots in root.findall("section[@name='Robots']"):
        for index in robots.findall("section[@name='index']"):
            for slot in index.findall("section"):
                idx = int(slot.get("name", -1))
                if 0 <= idx < len(race_config):
                    hex_color = race_config[idx].get("color", "#ff0000")
                    car_name  = _make_slot_car(idx, hex_color)
                    for attr in slot.findall("attstr"):
                        if attr.get("name") == "car name":
                            attr.set("val", car_name)
                    hx = hex_color.lstrip("#")
                    rf = int(hx[0:2], 16) / 255.0
                    gf = int(hx[2:4], 16) / 255.0
                    bf = int(hx[4:6], 16) / 255.0
                    for attr in slot.findall("attnum"):
                        if attr.get("name") == "red":   attr.set("val", f"{rf:.4f}")
                        if attr.get("name") == "green": attr.set("val", f"{gf:.4f}")
                        if attr.get("name") == "blue":  attr.set("val", f"{bf:.4f}")

    os.makedirs(os.path.dirname(SCR_SERVER_XML_DST), exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(SCR_SERVER_XML_DST, xml_declaration=True, encoding="UTF-8")
