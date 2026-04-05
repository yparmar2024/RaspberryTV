#!/bin/bash
# kiosk.sh — launched at boot via cron @reboot
# Waits for Flask to be ready, then starts X + Openbox + Chromium

export DISPLAY=:0
export XAUTHORITY=/home/rpitv/.Xauthority

# Wait for Flask on port 5000
echo "Waiting for Flask..."
for i in $(seq 1 30); do
  if curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo "Flask is up."
    break
  fi
  sleep 1
done

# Start X + Openbox in background
startx /usr/bin/openbox -- :0 vt1 &
sleep 4

# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# NOTE: unclutter intentionally removed — bluetooth mouse cursor must be visible

# Launch Chromium in kiosk mode with GPU acceleration
chromium \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-features=TranslateUI \
  --no-first-run \
  --check-for-update-interval=31536000 \
  --ignore-gpu-blocklist \
  --enable-zero-copy \
  --enable-features=VaapiVideoDecoder \
  --use-gl=egl \
  http://localhost:5000