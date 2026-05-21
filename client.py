# Web Server and UI for Python Race Orchestrator

import threading
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from server import state
from server.config import (
    DRIVER_PARAMS, SIMPLE_PARAMS, DEFAULT_SIMPLE, DRIVER_DISPLAY,
    MAX_CARS, MQTT_BROKER, MQTT_PORT,
)
from server.params import expand_simple_params
from server.history import (
    load_config, save_config,
    load_profiles, save_profiles,
    load_history,
)
from server.torcs_control import assign_ports
from server.telemetry_server import telemetry_listener
from server.race import do_launch, do_stop, handle_pi_command
from server import mqtt_bridge as _mqtt


# Handles what folder to look in for UI files
app = Flask(__name__, template_folder='ui', static_folder='ui/static')
app.secret_key = 'warpcore-mission-control'

# Redirect to login if not authenticated - exempts login page and static assets
@app.before_request
def require_login():
    if request.endpoint not in ('login', 'logout', 'static') and not session.get('logged_in'):
        return redirect(url_for('login'))

# Login page - accepts admin/password
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'password':
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'ACCESS DENIED — INVALID CREDENTIALS'
    return render_template('login.html', error=error)

# Clears session and returns to login
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

# Launches main page and assigns ports for cars in config json
@app.route("/")
def index():
    assign_ports()
    return render_template(
        "index.html",
        cars=state.race_config,
        driver_params=DRIVER_PARAMS,
        simple_params=SIMPLE_PARAMS,
        default_simple=DEFAULT_SIMPLE,
        driver_display=DRIVER_DISPLAY,
        running=bool(state.procs),
        profiles=state.profiles,
    )

# Handler for adding a new driver
@app.route("/add", methods=["POST"])
def add():
    if len(state.race_config) >= MAX_CARS:
        return redirect(url_for("index"))
    driver_type = request.form.get("type", "simple_ai")
    name = request.form.get("name", "").strip() or DRIVER_DISPLAY.get(driver_type, driver_type)
    simple = dict(DEFAULT_SIMPLE.get(driver_type, {}))
    params = expand_simple_params(driver_type, simple)
    state.race_config.append({"name": name, "type": driver_type, "params": params, "simple": simple})
    assign_ports()
    save_config()
    return redirect(url_for("index"))

# Handler for removing a driver 
@app.route("/remove/<int:idx>", methods=["POST"])
def remove(idx):
    if 0 <= idx < len(state.race_config):
        state.race_config.pop(idx)
        assign_ports()
        save_config()
    return redirect(url_for("index"))

# Handler for updating driver params
@app.route("/update/<int:idx>", methods=["POST"])
def update(idx):
    if not (0 <= idx < len(state.race_config)):
        return redirect(url_for("index"))
    car = state.race_config[idx]
    new_name = request.form.get("name", "").strip()
    if new_name:
        car["name"] = new_name

    # Switch between simple parameter adjustment and more advanced parameter adjustment
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

# Handlers for launching and stopping TORCS
@app.route("/launch", methods=["POST"])
def launch():
    do_launch()
    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop():
    do_stop()
    return redirect(url_for("index"))

# Handler for car telemetry
@app.route("/telemetry")
def get_telemetry():
    with state.lock:
        return jsonify(dict(state.telemetry))

# Returns race history
@app.route("/history")
def get_history():
    with state.lock:
        return jsonify(list(state.race_history))

# Allows for saving of driver profiles with specific parameters
@app.route("/profile/save", methods=["POST"])
def profile_save():
    idx   = int(request.form.get("idx", -1))
    pname = request.form.get("profile_name", "").strip()
    if not pname or not (0 <= idx < len(state.race_config)):
        return redirect(url_for("index"))
    car = state.race_config[idx]
    state.profiles.setdefault(car["type"], {})[pname] = dict(car.get("simple", {}))
    save_profiles()
    return redirect(url_for("index"))

# Load driver profiles
@app.route("/profile/load/<int:idx>", methods=["POST"])
def profile_load(idx):
    if not (0 <= idx < len(state.race_config)):
        return redirect(url_for("index"))
    pname = request.form.get("profile_name", "")
    car   = state.race_config[idx]
    simple = state.profiles.get(car["type"], {}).get(pname)
    if simple:
        car["simple"] = dict(simple)
        car["params"] = expand_simple_params(car["type"], simple)
        save_config()
    return redirect(url_for("index"))

# Delete driver profiles
@app.route("/profile/delete/<dtype>/<name>", methods=["POST"])
def profile_delete(dtype, name):
    if dtype in state.profiles and name in state.profiles[dtype]:
        del state.profiles[dtype][name]
        save_profiles()
    return redirect(url_for("index"))


if __name__ == "__main__":
    load_config()
    load_profiles()
    load_history()
    assign_ports()

    threading.Thread(target=telemetry_listener, daemon=True).start()

    # MQTT for communication with PI
    if _mqtt.AVAILABLE and MQTT_BROKER:
        state.mqtt_bridge = _mqtt.MQTTBridge(MQTT_BROKER, MQTT_PORT, handle_pi_command)
        state.mqtt_bridge.publish_state("idle")
        print(f"[MQTT] Connection Established → {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print("[MQTT] Disabled (set MQTT_BROKER to correct IP)")

    import logging

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print("UI running at http://localhost:3000")
    app.run(host="0.0.0.0", port=3000, debug=False)
