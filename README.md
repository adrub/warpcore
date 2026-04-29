# IBM TORCS RACE SIM 

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
 
If it prints `scr_server`, you're good.
 
---

## 5. Running TORCS
 
### Clone the repo
 
Open **Ubuntu** from the Start menu and run the following. Ensure you have Git installed:
 
```bash
cd ~
git clone https://github.com/adrub/warpcore.git
cd warpcore
```
 
### VS Code Setup

Install the Python, WSL and Remote Explorer extensions. 

To connect VS Code to Ubuntu, open VS Code on Windows and click the **Remote Explorer** icon in the left sidebar (or press `Ctrl+Shift+P` and search "WSL: Connect to WSL"). Click on your Ubuntu distro to connect. Once connected, the bottom-left corner of VS Code will show **WSL: Ubuntu**.
 
Then open the project: **File → Open Folder** → navigate to `/home/YOUR_USERNAME/warpcore` → click OK. You'll see all the project files in the sidebar.

The integrated terminal in VS Code (`` Ctrl+` ``) will now be an Ubuntu terminal — you'll use this to run the Python driver.

## 6. Running a Race
 
You need **two terminals open at the same time**:
 
### Terminal 1 — Ubuntu terminal (for TORCS)
 
Open Ubuntu from the **Start menu** (not the VS Code terminal) and run:
 
```bash
torcs
```
 
A TORCS window appears. Set up the race:
 
1. **Race → Quick Race → Configure Race**
2. Select the **Corkscrew** track
3. Add **scr_server 1** as a competitor
4. Set laps to 3
5. Click **Accept → New Race**
The car freezes on the grid. The terminal shows `Waiting for request on port 3001`. Leave it running.
 
### Terminal 2 — VS Code terminal (for Python)
 
In VS Code press `` Ctrl+` `` to open the integrated terminal. Run:
 
```bash
python3 filename.py
```
 
The car should start moving in TORCS and you'll see debug output in the VS Code terminal.
 
**Don't run TORCS from the VS Code terminal** — it needs its own terminal window for the graphical display.
 
---