import sqlite3
import os
from pathlib import Path

db_path = Path.home() / ".cortex" / "test_vec.db"
if db_path.exists():
    os.remove(db_path)

conn = sqlite3.connect(str(db_path))
conn.enable_load_extension(True)

# Try to find sqlite-vec extension
import platform

ext_path = None
if platform.system() == "Darwin":
    ext_path = "/usr/local/lib/vec0.dylib"  # common path
    # Try more paths if needed or rely on 'vec0'
    try:
        conn.load_extension("vec0")
        print("vec0 loaded successfully")

        conn.execute(
            "CREATE VIRTUAL TABLE test_vec USING vec0(id INTEGER PRIMARY KEY, embedding FLOAT[4])"
        )
        conn.execute("INSERT INTO test_vec(id, embedding) VALUES (1, '[1,2,3,4]')")

        # Test if IVF index creation is supported via standard SQL (hypothetical for now)
        try:
            # Some versions use a specific syntax or shadow tables.
            # Let's check if we can just create a basic index.
            print("Checking index support...")
            # conn.execute("CREATE INDEX idx_test ON test_vec(embedding)") # This usually fails on virtual tables
        except Exception as e:
            print(f"Index failed: {e}")

    except Exception as e:
        print(f"Failed to load vec0: {e}")

conn.close()
if db_path.exists():
    os.remove(db_path)
