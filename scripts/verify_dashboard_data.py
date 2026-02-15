
import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cortex.timing import TimingTracker, TimeSummary

def verify_daily_data():
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    tracker = TimingTracker(conn)
    
    print("--- Verifying matches for daily() ---")
    daily_stats = tracker.daily(days=7)
    print(daily_stats)
    
    total_seconds = sum(d['seconds'] for d in daily_stats)
    print(f"Total seconds in last 7 days: {total_seconds}")
    print(f"Total hours: {total_seconds / 3600:.2f}")

    if total_seconds > 0:
        print("✅ Data found for chart.")
    else:
        print("⚠️ No data found (Simulation might be needed if this is 0).")

if __name__ == "__main__":
    verify_daily_data()
