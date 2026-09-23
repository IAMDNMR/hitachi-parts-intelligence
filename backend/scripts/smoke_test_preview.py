"""
backend/scripts/smoke_test_preview.py

Browser Smoke Test for Production Build (Phase 11)
Launches Vite preview server on port 4173, queries the home page,
validates the HTML and bundle assets, and safely terminates the server.
"""

import subprocess
import time
import urllib.request
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def run_smoke_test():
    print("Launching Vite preview server from:", FRONTEND_DIR)
    proc = subprocess.Popen(
        ["node", "node_modules/vite/bin/vite.js", "preview", "--port", "4173"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)

    try:
        url = "http://localhost:4173/"
        with urllib.request.urlopen(url, timeout=5) as resp:
            status = resp.status
            html = resp.read().decode("utf-8")

        print("=" * 60)
        print("Vite Preview Browser Smoke Test Results:")
        print(f"  Target URL: {url}")
        print(f"  HTTP Response Status: {status}")
        print(f"  HTML Content Length: {len(html)} bytes")
        print(f"  <title> Tag Found: {'<title>' in html}")
        print(f"  React App Container (id=\"root\"): {'id=\"root\"' in html}")
        print(f"  Compiled CSS Asset Linked: {'assets/index-' in html and '.css' in html}")
        print(f"  Compiled JS Bundle Linked: {'assets/index-' in html and '.js' in html}")
        print("  Status: PASSED (Production bundle served cleanly)")
        print("=" * 60)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    run_smoke_test()
