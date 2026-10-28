#!/usr/bin/env bash
set -euo pipefail

SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}"
CMDLINE_ZIP="commandlinetools-linux-11076708_latest.zip"
CMDLINE_URL="https://dl.google.com/android/repository/${CMDLINE_ZIP}"

echo "[*] installing packages..."
sudo apt-get update -y
sudo apt-get install -y openjdk-17-jdk unzip wget curl python3 python3-pip

echo "[*] fetching android cmdline-tools..."
mkdir -p "$SDK_ROOT/cmdline-tools"
cd "$SDK_ROOT/cmdline-tools"
if [ ! -d latest ]; then
  wget -q "$CMDLINE_URL" -O cmdline.zip
  unzip -q cmdline.zip
  mv cmdline-tools latest
  rm cmdline.zip
fi

export PATH="$SDK_ROOT/cmdline-tools/latest/bin:$SDK_ROOT/platform-tools:$PATH"

echo "[*] accepting licenses..."
yes | sdkmanager --licenses > /dev/null || true

echo "[*] installing SDK pieces..."
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" > /dev/null

echo "[*] installing cloudflared..."
if ! command -v cloudflared >/dev/null 2>&1; then
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -O /tmp/cfd.deb
  sudo dpkg -i /tmp/cfd.deb || sudo apt-get install -y -f
  rm -f /tmp/cfd.deb
fi

echo "[*] done."
echo "    add to your shell rc:"
echo "    export ANDROID_SDK_ROOT=$SDK_ROOT"
echo "    export PATH=\$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:\$ANDROID_SDK_ROOT/platform-tools:\$PATH"
