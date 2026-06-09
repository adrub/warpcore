[← Back to README](../README.md)

# Installation Guide

---

## 1. Install WSL2

Open **PowerShell as Administrator** (search PowerShell → right-click → Run as administrator):

```powershell
wsl --install
```

Restart your PC when prompted. After restart, Ubuntu opens and asks you to pick a username and password — choose anything simple, you'll need the password for `sudo` commands later.

If WSL is already installed, just open Ubuntu from the Start menu. If you don't see Ubuntu or it doesn't work you can also install it from the Microsoft Store.

---

## 2. Install dependencies

Open **Ubuntu** from the Start menu and run:

```bash
sudo apt-get update
```

Then run:

```bash
sudo apt-get install -y build-essential git libglib2.0-dev libgl1-mesa-dev libglu1-mesa-dev freeglut3-dev libpng-dev libjpeg-dev libvorbis-dev libopenal-dev libalut-dev libxi-dev libxmu-dev libxrender-dev libxrandr-dev libfreetype6-dev libxxf86vm-dev libplib-dev
```

Wait for it to finish.

Then install the tools the control panel itself needs — `xdotool` (lets the wrapper drive the TORCS menus automatically) and the Python libraries (Flask web server, Pillow for the car colours, paho-mqtt for the Raspberry Pi link):

```bash
sudo apt-get install -y xdotool python3-flask python3-pil python3-paho-mqtt
```

---

## 3. Clone and compile TORCS

```bash
cd ~
git clone https://github.com/fmirus/torcs-1.3.7.git
cd torcs-1.3.7
export TORCS_BASE=$(pwd)
export MAKE_DEFAULT=$TORCS_BASE/Make-default.mk
make
```

`make` takes about 15 minutes. You'll see lots of warnings — **ignore all warnings**, they're fine. Only stop if you see `error` and the build halts.

When make finishes:

```bash
sudo make install
sudo make datainstall
```

---

## 4. Check it worked

```bash
ls /usr/local/lib/torcs/drivers/ | grep scr
```

If it prints `scr_server`, it has installed properly.

Change the car models to the F1 car as follows:

```bash
sudo sed -i 's/car1-trb1/car1-ow1/g' /usr/local/share/games/torcs/drivers/scr_server/scr_server.xml
```

---

## 5. Clone the repo

Open **Ubuntu** from the Start menu and run:

```bash
cd ~
git clone https://github.com/adrub/warpcore.git
cd warpcore
```

### VS Code Setup

Install the Python, WSL and Remote Explorer extensions.

To connect VS Code to Ubuntu, open VS Code on Windows and click the **Remote Explorer** icon in the left sidebar (or press `Ctrl+Shift+P` and search "WSL: Connect to WSL"). Click on your Ubuntu distro to connect. Once connected, the bottom-left corner of VS Code will show **WSL: Ubuntu**.

Then open the project: **File → Open Folder** → navigate to `/home/YOUR_USERNAME/warpcore` → click OK. You'll see all the project files in the sidebar.

The integrated terminal in VS Code (`` Ctrl+` ``) will now be an Ubuntu terminal.

---

## 6. Running the Control Panel

This is the normal way to run everything — the Python wrapper launches TORCS and the cars for you, no manual setup.

From the project folder:

```bash
cd ~/warpcore
python3 client.py
```

It prints `UI running at http://localhost:5000`. Open that address in your **Windows browser** (WSL forwards `localhost` automatically) and log in:

- **Username:** `admin`
- **Password:** `password`

Add one or more drivers, give them colours, then press **Launch Race** (or `PF5`). TORCS opens and the cars race automatically; live telemetry, graphs and the track map appear on the page. **Stop Race** (`PF12`) ends it.

> **Using a Raspberry Pi** for the lights/buttons? Set `MQTT_BROKER` in `server/config.py` to the broker's IP first. If you're **not** using the Pi, leave it as `localhost` — MQTT just stays disabled and everything else works.

### Testing a single driver by hand (optional)

To run one driver against a manually-started TORCS (no wrapper): open TORCS from the **Start menu** with `torcs`, set up a Quick Race on **Corkscrew** with **scr_server 1**, then in a second terminal run e.g. `python3 simple_ai.py --port 3001`.

---

## 7. Troubleshooting

**`make` fails with "cannot find -lSOMETHING"**

You're missing a library. Run `sudo apt-get install -y libSOMETHING-dev` replacing SOMETHING with whatever it says is missing, then run `make` again.

**`scr_server` not in TORCS driver list**

The compile didn't fully work. Go back to the torcs folder and re-run:

```bash
cd ~/torcs-1.3.7
export TORCS_BASE=$(pwd)
export MAKE_DEFAULT=$TORCS_BASE/Make-default.mk
make
sudo make install
sudo make datainstall
```

Also make sure GitHub CLI is installed in Ubuntu to push changes.
