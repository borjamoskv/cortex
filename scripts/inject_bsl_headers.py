import os
from pathlib import Path

BSL_HEADER = """# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)
"""


def inject_header(file_path):
    content = file_path.read_text()
    if BSL_HEADER.strip() in content:
        print(f"[-] Skip: {file_path.name} (Header exists)")
        return

    # Prepend header
    new_content = BSL_HEADER + "\n" + content
    file_path.write_text(new_content)
    print(f"[+] Injected: {file_path.name}")


def main():
    base_dir = Path(__file__).parent.parent
    cortex_dir = base_dir / "cortex"

    for root, _, files in os.walk(cortex_dir):
        for file in files:
            if file.endswith(".py"):
                inject_header(Path(root) / file)


if __name__ == "__main__":
    main()
