import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"


def test_rate_limit():
    print("Testing Rate Limit...")
    # Hit status endpoint repeatedly
    success = 0
    blocked = 0
    start = time.time()
    for i in range(350):
        try:
            r = requests.get(f"{BASE_URL}/v1/status")
            if r.status_code == 200:
                success += 1
            elif r.status_code == 429:
                blocked += 1
                break
        except Exception as e:
            print(f"Request failed: {e}")
            break

    end = time.time()
    print(f"Sent {success + blocked} requests in {end - start:.2f}s")
    print(f"Success: {success}, Blocked: {blocked}")

    if blocked > 0:
        print("✅ Rate Limiting works!")
    else:
        print("❌ Rate Limiting failed (or limit too high)")


def test_cors():
    print("\nTesting CORS...")
    headers = {"Origin": "http://evil-site.com", "Access-Control-Request-Method": "GET"}
    r = requests.options(f"{BASE_URL}/v1/status", headers=headers)
    print(f"Status: {r.status_code}")
    allow_origin = r.headers.get("Access-Control-Allow-Origin")
    print(f"Allow-Origin: {allow_origin}")

    if allow_origin is None or allow_origin != "http://evil-site.com":
        print("✅ CORS protects against evil-site.com (Origin not reflected)")
    else:
        print("❌ CORS failed: Origin reflected!")

    # Test allowed origin
    headers["Origin"] = "http://localhost:3000"
    r = requests.options(f"{BASE_URL}/v1/status", headers=headers)
    allow_origin = r.headers.get("Access-Control-Allow-Origin")
    if allow_origin == "http://localhost:3000":
        print("✅ CORS allows localhost:3000")
    else:
        print(f"❌ CORS failed for localhost:3000 (got {allow_origin})")


if __name__ == "__main__":
    try:
        # verify server is up
        r = requests.get(f"{BASE_URL}/")
        if r.status_code != 200:
            print(f"Server returned {r.status_code}")
            sys.exit(1)

        test_cors()
        test_rate_limit()

    except requests.exceptions.ConnectionError:
        print("❌ Server not running on port 8000")
