# IBM TORCS RACE SIM 

## 1. Install WSL2
 
Open **PowerShell as Administrator** (search PowerShell → right-click → Run as administrator):
 
```powershell
wsl --install
```
 
Restart your PC when prompted. After restart, Ubuntu opens and asks you to pick a username and password — choose anything simple, you'll need the password for `sudo` commands later.
 
If WSL is already installed, just open Ubuntu from the Start menu.
 
---
 
## 2. Install dependencies
 
Open **Ubuntu** from the Start menu and run:
 
```bash
sudo apt-get update
```
 
Then:
 
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

