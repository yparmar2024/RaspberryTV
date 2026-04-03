# RaspberryTV 🎬

TV-optimized movie & TV browser for Raspberry Pi. Controlled via a phone remote using WebSockets — no CEC, no xdotool, no VNC.

## Architecture

```
Phone browser (/remote) ──WebSocket──┐
                                     ├── Flask + SocketIO (:5000) ── TMDB API
TV browser (/) ──────────WebSocket──┘                             └── VidKing
```

## Setup on Raspberry Pi

### 1. Clone
```bash
cd ~
git clone https://github.com/yparmar2024/RaspberryTV.git
cd RaspberryTV
```

### 2. Secrets
```bash
cp .env.example .env
nano .env   # paste your TMDB_API_KEY
```

### 3. Install Python deps
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install eventlet   # required for flask-socketio with gunicorn
```

### 4. Test it
```bash
python app.py
# Open http://<pi-ip>:5000 in a browser to confirm it works
# Ctrl+C when done
```

### 5. Flask systemd service
```bash
mkdir -p ~/RaspberryTV/logs
sudo cp ~/RaspberryTV/raspberrytv.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable raspberrytv
sudo systemctl start raspberrytv
sudo systemctl status raspberrytv
```

### 6. Kiosk auto-start via cron
```bash
chmod +x ~/RaspberryTV/kiosk.sh
crontab -e
```
Add this line:
```
@reboot /home/rpitv/RaspberryTV/kiosk.sh >> /home/rpitv/RaspberryTV/logs/kiosk.log 2>&1
```

### 7. Console autologin
```bash
sudo raspi-config
# System Options → Boot / Auto Login → Console Autologin
```

### 8. Reboot
```bash
sudo reboot
```

## Usage

- **TV browser**: loads automatically at `http://localhost:5000`
- **Phone remote**: open `http://<pi-ip>:5000/remote` on your phone
- **Away from home**: use Tailscale IP `http://100.x.x.x:5000/remote`

## Deploying updates

```bash
# Mac
git add . && git commit -m "..." && git push

# Pi
cd ~/RaspberryTV && git pull && sudo systemctl restart raspberrytv
```

## Remote controls

| Button | Action |
|--------|--------|
| D-pad | Navigate cards |
| OK | Select / Open |
| Back | Close panel / Escape |
| Home | Return to trending |
| Search bar | Type query → Search button sends it to TV |
