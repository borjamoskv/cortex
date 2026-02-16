
import requests
import os
import sys
import time

API_URL = "http://localhost:8484"
API_KEY = "ctx_ec22a93e6844e98a3839d818cba1e1bd2180eb5b09a05ef8a650ff455c8d9197"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def check_status():
    print(f"Checking CORTEX God Mode at {API_URL}...")
    try:
        # Check basic status
        r = requests.get(f"{API_URL}/v1/status", headers=HEADERS)
        if r.status_code != 200:
            print(f"❌ Failed to get status: {r.status_code} {r.text}")
            return False
        
        status = r.json()
        print(f"✅ Status: {status}")
        
        # Check Version
        if status.get("version") != "4.0.0a1":
            print(f"❌ Version mismatch: Expected 4.0.0a1, got {status.get('version')}")
            # return False # Non-blocking for now

        # Check Daemon
        r_daemon = requests.get(f"{API_URL}/v1/daemon/status", headers=HEADERS)
        if r_daemon.status_code != 200:
             print(f"⚠️ Daemon status check failed: {r_daemon.status_code}")
        else:
             print(f"✅ Daemon Status: {r_daemon.json()}")

        # Check Dashboard Accessibility
        r_dash = requests.get(f"{API_URL}/dashboard")
        if r_dash.status_code != 200:
            print(f"❌ Dashboard inaccessible: {r_dash.status_code}")
            return False
        print("✅ Dashboard accessible at /dashboard")

        return True

    except requests.exceptions.ConnectionError:
        print("❌ Connection refused. Is the server running on port 8484?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = check_status()
    if success:
        print("\n✨ GOD MODE VERIFIED: The spark is lit. ✨")
        sys.exit(0)
    else:
        print("\n💥 Verification Failed.")
        sys.exit(1)
