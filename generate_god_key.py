"""
Generate CORTEX API Key directly via AuthManager.
"""

import os
from cortex.auth import AuthManager

# Ensure we use the default DB path
DB_PATH = os.path.expanduser("~/.cortex/cortex.db")


def generate_key():
    print(f"📂 Opening CORTEX DB at: {DB_PATH}")
    auth = AuthManager(DB_PATH)

    # Create a key with admin permissions
    name = "god_mode_swarn"
    print(f"🔑 Generating key for: {name}")

    try:
        raw_key, api_key = auth.create_key(name=name, permissions=["read", "write", "admin"])
        print("\n✅ API KEY GENERATED SUCCESSFULLY:")
        print(f"Key: {raw_key}")
        print(f"Prefix: {api_key.key_prefix}")
        print(f"Permissions: {api_key.permissions}")

        # Save to .env in moskv-swarm for convenience
        env_path = os.path.expanduser("~/game/moskv-swarm/.env")
        with open(env_path, "a") as f:
            f.write(f"\n# Added by God Mode Setup\nCORTEX_API_KEY={raw_key}\n")
        print(f"\n💾 Appended to {env_path}")

    except Exception as e:
        print(f"\n❌ Error generating key: {e}")


if __name__ == "__main__":
    generate_key()
