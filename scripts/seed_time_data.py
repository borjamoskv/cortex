import sys
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure we can import from cortex
sys.path.append(os.getcwd())

from cortex.timing import TimingTracker
from cortex.engine import CortexEngine

# Configuration
DB_PATH = Path.home() / ".cortex/cortex.db"
PROJECT_CORTEX = "cortex"
PROJECT_NAROA = "naroa-web"

# Time ranges (relative to NOW)
# 8 hours ago -> Start of day
NOW = datetime.now(timezone.utc)
START_OF_DAY = NOW - timedelta(hours=8)

SCHEDULE = [
    # 09:00 - 11:30: Backend Work (Cortex)
    {
        "start_offset": timedelta(minutes=0),
        "duration": timedelta(minutes=150),
        "project": PROJECT_CORTEX,
        "files": ["cortex/api.py", "cortex/engine.py", "cortex/auth.py", "tests/test_api.py"],
        "category": "coding",
    },
    # 11:30 - 12:00: Comms
    {
        "start_offset": timedelta(minutes=150),
        "duration": timedelta(minutes=30),
        "project": "communications",
        "files": ["Slack", "Discord", "Email"],
        "category": "comms",
    },
    # 12:00 - 13:00: Lunch Breakdown (No data)
    {
        "start_offset": timedelta(minutes=180),
        "duration": timedelta(minutes=60),
        "project": None,  # Break
        "files": [],
        "category": None,
    },
    # 13:00 - 15:00: Frontend Work (Naroa)
    {
        "start_offset": timedelta(minutes=240),
        "duration": timedelta(minutes=120),
        "project": PROJECT_NAROA,
        "files": ["src/components/Gallery.tsx", "src/styles/main.css", "public/index.html"],
        "category": "coding",
    },
    # 15:00 - 16:30: Documentation
    {
        "start_offset": timedelta(minutes=360),
        "duration": timedelta(minutes=90),
        "project": PROJECT_CORTEX,
        "files": ["README.md", "docs/API.md", "docs/ARCHITECTURE.md"],
        "category": "docs",
    },
    # 16:30 - 17:00: Code Review
    {
        "start_offset": timedelta(minutes=450),
        "duration": timedelta(minutes=30),
        "project": PROJECT_CORTEX,
        "files": ["Pull Request #42", "Pull Request #43"],
        "category": "development",
    },
]


def seed():
    days_to_simulate = 30
    print(f"🌱 Seeding data for the last {days_to_simulate} days...")

    # Initialize via Engine to ensure schema exists
    engine = CortexEngine(db_path=DB_PATH)
    engine.init_db()
    conn = engine._get_conn()

    tracker = TimingTracker(conn)

    # CLEAR OLD DATA
    print("🧹 Cleaning old timing data...")
    conn.execute("DELETE FROM heartbeats")
    conn.execute("DELETE FROM time_entries")
    conn.commit()

    total_heartbeats = 0

    for day_offset in range(days_to_simulate, -1, -1):
        # Current day in loop (from 30 days ago to today)
        current_date_base = NOW - timedelta(days=day_offset)

        # Randomize start of day (08:30 - 09:30)
        start_hour = 8 + random.random()
        day_start = current_date_base.replace(
            hour=int(start_hour), minute=int((start_hour % 1) * 60), second=0, microsecond=0
        )

        print(f"  📅 Generating for {day_start.date()}...")

        for block in SCHEDULE:
            if not block["project"]:
                continue

            # Add some randomness to block start/duration
            jitter = random.randint(-10, 10)

            block_start = day_start + block["start_offset"] + timedelta(minutes=jitter)
            block_end = block_start + block["duration"]

            # Skip if strict future (though NOW is the limit, backdating is fine)
            if block_start > NOW:
                continue

            current_time = block_start

            while current_time < block_end and current_time < NOW:
                # Simulate a heartbeat every ~2 minutes
                interval = random.randint(90, 150)  # 1.5 - 2.5 minutes

                # Select a random file
                entity = random.choice(block["files"])

                ts_str = current_time.isoformat()

                lang = "text"
                if entity.endswith(".py"):
                    lang = "python"
                elif entity.endswith(".js") or entity.endswith(".tsx"):
                    lang = "javascript"
                elif entity.endswith(".md"):
                    lang = "markdown"
                elif entity.endswith(".css"):
                    lang = "css"

                conn.execute(
                    """
                    INSERT INTO heartbeats 
                    (timestamp, project, entity, category, branch, language, meta)
                    VALUES (?, ?, ?, ?, ?, ?, '{}')
                    """,
                    (ts_str, block["project"], entity, block["category"], "main", lang),
                )

                total_heartbeats += 1
                current_time += timedelta(seconds=interval)

    conn.commit()
    print(f"✅ Generated {total_heartbeats} heartbeats across {days_to_simulate} days.")

    print("🔄 Flushing to time_entries...")
    tracker.flush()
    print("✅ Done.")
    conn.close()


if __name__ == "__main__":
    seed()
