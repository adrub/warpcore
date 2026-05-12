import datetime
import json
import os
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, redirect, render_template, request, url_for

app = Flask(__name__, template_folder='ui')

CONFIG_FILE   = os.path.join(os.path.dirname(__file__), "race_config.json")
PROFILES_FILE = os.path.join(os.path.dirname(__file__), "profiles.json")
HISTORY_FILE  = os.path.join(os.path.dirname(__file__), "race_history.json")
QUICKRACE_XML = os.path.expanduser("~/.torcs/config/raceman/quickrace.xml")
TELEMETRY_PORT = 9999
MAX_CARS = 10

# ── Raw params (used in Advanced view and by drivers) ─────────────────────────

DRIVER_PARAMS = {
    "simple_ai": {
        "angle_gain": 0.5,
        "position_gain": 0.3,
        "upshift_threshold": 0.9,
        "downshift_rpm": 8000,
        "straight_throttle": 1.0,
        "medium_corner_throttle": 0.85,
        "tight_corner_throttle": 0.5,
        "brake_emergency_speed": 50,
        "brake_emergency_range": 18,
        "brake_emergency_force": 0.85,
        "brake_hard_speed": 120,
        "brake_hard_range": 55,
        "brake_hard_force": 0.65,
        "brake_soft_speed": 80,
        "brake_soft_range": 35,
        "brake_soft_force": 0.4,
        "opp_brake_dist": 8,
        "opp_slow_dist": 20,
        "opp_overtake_offset": 0.4,
        "opp_clear_dist": 30,
    },
    "pid_ai": {
        "steer_kp": 0.3,
        "steer_ki": 0.0,
        "steer_kd": 0.5,
        "upshift_threshold": 0.9,
        "downshift_rpm": 9500,
        "straight_throttle": 1.0,
        "medium_corner_throttle": 0.85,
        "tight_corner_throttle": 0.5,
        "brake_emergency_speed": 50,
        "brake_emergency_range": 28,
        "brake_emergency_force": 0.85,
        "brake_early_speed": 100,
        "brake_early_range": 110,
        "brake_early_force": 0.45,
        "brake_hard_speed": 75,
        "brake_hard_range": 75,
        "brake_hard_force": 0.65,
        "brake_soft_speed": 45,
        "brake_soft_range": 35,
        "brake_soft_force": 0.3,
        "centered_threshold": 0.5,
        "opp_brake_dist": 8,
        "opp_slow_dist": 20,
        "opp_overtake_offset": 0.4,
        "opp_clear_dist": 30,
    },
}

# ── Normalised slider schema (used in simple view) ────────────────────────────

_BRAKING_SLIDERS = [
    {"key": "brake_force",    "label": "Brake Force",    "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "brake_distance", "label": "Brake Distance", "min": 0.0, "max": 1.0, "step": 0.05},
]
_ACCEL_SLIDERS = [
    {"key": "shift_aggression", "label": "Shift Aggression", "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "straight_speed",   "label": "Straight Speed",   "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "corner_caution",   "label": "Corner Caution",   "min": 0.0, "max": 1.0, "step": 0.05},
]
_OPP_SLIDERS = [
    {"key": "opp_aggressiveness", "label": "Aggressiveness",   "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "opp_detection",      "label": "Detection Range",  "min": 0.0, "max": 1.0, "step": 0.05},
]

SIMPLE_PARAMS = {
    "pid_ai": {
        "PID Control": [
            {"key": "steer_kp", "label": "Proportional (Kp)", "min": 0.0, "max": 2.0,  "step": 0.05,  "direct": True},
            {"key": "steer_ki", "label": "Integral (Ki)",     "min": 0.0, "max": 0.2,  "step": 0.005, "direct": True},
            {"key": "steer_kd", "label": "Derivative (Kd)",   "min": 0.0, "max": 2.0,  "step": 0.05,  "direct": True},
        ],
        "Braking":              _BRAKING_SLIDERS,
        "Acceleration":         _ACCEL_SLIDERS,
        "Opponent Behaviour":   _OPP_SLIDERS,
    },
    "simple_ai": {
        "Steering": [
            {"key": "steering_responsiveness", "label": "Responsiveness", "min": 0.0, "max": 1.0, "step": 0.05},
        ],
        "Braking":            _BRAKING_SLIDERS,
        "Acceleration":       _ACCEL_SLIDERS,
        "Opponent Behaviour": _OPP_SLIDERS,
    },
}

DEFAULT_SIMPLE = {
    "pid_ai": {
        "steer_kp": 0.3, "steer_ki": 0.0, "steer_kd": 0.5,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_aggressiveness": 0.5, "opp_detection": 0.6,
    },
    "simple_ai": {
        "steering_responsiveness": 0.5,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_aggressiveness": 0.5, "opp_detection": 0.6,
    },
}

DRIVER_FILES = {"simple_ai": "simple_ai.py", "pid_ai": "pid_ai.py"}
DRIVER_DISPLAY = {"simple_ai": "SimpleAI", "pid_ai": "PidAI"}

# ── State ─────────────────────────────────────────────────────────────────────

race_config  = []
procs        = []
telemetry    = {}
race_history = []
profiles     = {"pid_ai": {}, "simple_ai": {}}
_lock        = threading.Lock()


# ── Lerp + param expansion ────────────────────────────────────────────────────

def _lerp(a, b, t):
    return a + (b - a) * t


def expand_simple_params(driver_type, simple):
    bf = simple.get("brake_force",    0.6)
    bd = simple.get("brake_distance", 0.7)
    sa = simple.get("shift_aggression", 0.5)
    ss = simple.get("straight_speed",   0.8)
    cc = simple.get("corner_caution",   0.5)
    oa = simple.get("opp_aggressiveness", 0.5)
    od = simple.get("opp_detection",      0.6)

    raw = {
        # Braking forces
        "brake_emergency_force": _lerp(0.3,  1.0,  bf),
        "brake_hard_force":      _lerp(0.15, 0.8,  bf),
        "brake_early_force":     _lerp(0.1,  0.6,  bf),
        "brake_soft_force":      _lerp(0.05, 0.35, bf),
        # Braking speeds
        "brake_emergency_speed": _lerp(30,  70,  bf),
        "brake_hard_speed":      _lerp(40,  100, bf),
        "brake_early_speed":     _lerp(60,  140, bf),
        "brake_soft_speed":      _lerp(30,  65,  bf),
        # Braking ranges
        "brake_emergency_range": _lerp(15,  40,  bd),
        "brake_early_range":     _lerp(50,  150, bd),
        "brake_hard_range":      _lerp(35,  100, bd),
        "brake_soft_range":      _lerp(15,  55,  bd),
        # Acceleration
        "upshift_threshold":       _lerp(0.75, 0.95,  sa),
        "downshift_rpm":           _lerp(7000, 12000, sa),
        "straight_throttle":       _lerp(0.5,  1.0,   ss),
        "medium_corner_throttle":  _lerp(0.95, 0.5,   cc),
        "tight_corner_throttle":   _lerp(0.8,  0.2,   cc),
        # Opponents
        "opp_overtake_offset": _lerp(0.2, 0.7,  oa),
        "opp_brake_dist":      _lerp(15,  4,    oa),
        "opp_slow_dist":       _lerp(10,  35,   od),
        "opp_clear_dist":      _lerp(15,  50,   od),
    }

    if driver_type == "pid_ai":
        raw["steer_kp"] = simple.get("steer_kp", 0.3)
        raw["steer_ki"] = simple.get("steer_ki", 0.0)
        raw["steer_kd"] = simple.get("steer_kd", 0.5)
        raw["centered_threshold"] = 0.5
    elif driver_type == "simple_ai":
        sr = simple.get("steering_responsiveness", 0.5)
        raw["angle_gain"]    = _lerp(0.2, 1.0, sr)
        raw["position_gain"] = _lerp(0.1, 0.6, sr)

    return raw


# ── Persistence ───────────────────────────────────────────────────────────────

def load_config():
    global race_config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            race_config = json.load(f)
        for car in race_config:
            if "simple" not in car:
                car["simple"] = dict(DEFAULT_SIMPLE.get(car.get("type", ""), {}))


def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(race_config, f, indent=2)


def load_profiles():
    global profiles
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            profiles = json.load(f)
    profiles.setdefault("pid_ai", {})
    profiles.setdefault("simple_ai", {})


def save_profiles():
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)


def load_history():
    global race_history
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            race_history = json.load(f)


def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(race_history, f, indent=2)


# ── Helpers ───────────────────────────────────────────────────────────────────

def assign_ports():
    for i, car in enumerate(race_config):
        car["port"] = 3001 + i


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


def _xdotool(*args):
    r = subprocess.run(["xdotool", *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def _quit_torcs():
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


def _autostart_torcs():
    print("[autostart] Waiting for TORCS window...")
    wid = None
    for _ in range(30):
        code, out = _xdotool("search", "--name", "torcs")
        if code == 0 and out:
            wid = out.splitlines()[0]
            break
        time.sleep(0.5)
    if not wid:
        print("[autostart] TORCS window not found — start race manually")
        return
    print(f"[autostart] Found window {wid}, navigating menu...")
    time.sleep(2.0)
    _xdotool("windowfocus", "--sync", wid)
    time.sleep(0.3)
    for key, delay in [("Return", 1.0), ("Return", 1.0), ("Return", 1.0), ("Return", 0.5)]:
        _xdotool("key", "--window", wid, key)
        time.sleep(delay)
    print("[autostart] Race started.")


def telemetry_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", TELEMETRY_PORT))
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            entry = json.loads(data.decode())
            name = entry["name"]
            with _lock:
                prev      = telemetry.get(name, {})
                prev_last = prev.get("last_lap", 0)
                new_last  = entry.get("last_lap", 0)

                entry["laps"]     = prev.get("laps", 0)
                entry["best_lap"] = prev.get("best_lap", 0)

                if new_last > 0 and new_last != prev_last:
                    entry["laps"] = prev.get("laps", 0) + 1
                    if entry["best_lap"] == 0 or new_last < entry["best_lap"]:
                        entry["best_lap"] = new_last
                    race_history.append({
                        "name": name,
                        "lap": entry["laps"],
                        "lap_time": round(new_last, 3),
                        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                    })
                    save_history()

                telemetry[name] = entry
        except Exception:
            pass


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    assign_ports()
    return render_template(
        "index.html",
        cars=race_config,
        driver_params=DRIVER_PARAMS,
        simple_params=SIMPLE_PARAMS,
        default_simple=DEFAULT_SIMPLE,
        driver_display=DRIVER_DISPLAY,
        running=bool(procs),
        profiles=profiles,
    )


@app.route("/add", methods=["POST"])
def add():
    if len(race_config) >= MAX_CARS:
        return redirect(url_for("index"))
    driver_type = request.form.get("type", "simple_ai")
    name = request.form.get("name", "").strip() or DRIVER_DISPLAY.get(driver_type, driver_type)
    simple = dict(DEFAULT_SIMPLE.get(driver_type, {}))
    params = expand_simple_params(driver_type, simple)
    race_config.append({"name": name, "type": driver_type, "params": params, "simple": simple})
    assign_ports()
    save_config()
    return redirect(url_for("index"))


@app.route("/remove/<int:idx>", methods=["POST"])
def remove(idx):
    if 0 <= idx < len(race_config):
        race_config.pop(idx)
        assign_ports()
        save_config()
    return redirect(url_for("index"))


@app.route("/update/<int:idx>", methods=["POST"])
def update(idx):
    if not (0 <= idx < len(race_config)):
        return redirect(url_for("index"))
    car = race_config[idx]
    new_name = request.form.get("name", "").strip()
    if new_name:
        car["name"] = new_name

    mode = request.form.get("mode", "simple")
    if mode == "simple":
        simple = car.setdefault("simple", dict(DEFAULT_SIMPLE.get(car["type"], {})))
        for sliders in SIMPLE_PARAMS.get(car["type"], {}).values():
            for s in sliders:
                val = request.form.get(s["key"])
                if val is not None:
                    try:
                        simple[s["key"]] = float(val)
                    except ValueError:
                        pass
        car["params"] = expand_simple_params(car["type"], simple)
    else:
        for key in DRIVER_PARAMS.get(car["type"], {}):
            val = request.form.get(key)
            if val is not None:
                try:
                    car["params"][key] = float(val)
                except ValueError:
                    pass

    save_config()
    return redirect(url_for("index"))


@app.route("/launch", methods=["POST"])
def launch():
    global procs
    if procs or not race_config:
        return redirect(url_for("index"))
    assign_ports()
    patch_quickrace_xml(len(race_config))

    procs.append(subprocess.Popen(["torcs"]))
    threading.Thread(target=_autostart_torcs, daemon=True).start()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    for car in race_config:
        params = dict(car["params"])
        params["telemetry_port"] = TELEMETRY_PORT
        cmd = [
            sys.executable, "-u",
            os.path.join(base_dir, DRIVER_FILES[car["type"]]),
            "--port", str(car["port"]),
            "--name", car["name"],
            "--params", json.dumps(params),
        ]
        procs.append(subprocess.Popen(cmd))
    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop():
    global procs
    _quit_torcs()
    for p in procs:
        try:
            p.kill()
        except Exception:
            pass
    procs.clear()
    with _lock:
        telemetry.clear()
    return redirect(url_for("index"))


@app.route("/telemetry")
def get_telemetry():
    with _lock:
        return jsonify(dict(telemetry))


@app.route("/history")
def get_history():
    with _lock:
        return jsonify(list(race_history))


@app.route("/profile/save", methods=["POST"])
def profile_save():
    idx   = int(request.form.get("idx", -1))
    pname = request.form.get("profile_name", "").strip()
    if not pname or not (0 <= idx < len(race_config)):
        return redirect(url_for("index"))
    car = race_config[idx]
    profiles.setdefault(car["type"], {})[pname] = dict(car.get("simple", {}))
    save_profiles()
    return redirect(url_for("index"))


@app.route("/profile/load/<int:idx>", methods=["POST"])
def profile_load(idx):
    if not (0 <= idx < len(race_config)):
        return redirect(url_for("index"))
    pname = request.form.get("profile_name", "")
    car   = race_config[idx]
    simple = profiles.get(car["type"], {}).get(pname)
    if simple:
        car["simple"] = dict(simple)
        car["params"] = expand_simple_params(car["type"], simple)
        save_config()
    return redirect(url_for("index"))


@app.route("/profile/delete/<dtype>/<name>", methods=["POST"])
def profile_delete(dtype, name):
    if dtype in profiles and name in profiles[dtype]:
        del profiles[dtype][name]
        save_profiles()
    return redirect(url_for("index"))


if __name__ == "__main__":
    load_config()
    load_profiles()
    load_history()
    assign_ports()
    threading.Thread(target=telemetry_listener, daemon=True).start()
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print("Warp-Core client running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
