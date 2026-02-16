import os
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor

# Constants
VENV_DIR = ".venv"
IGNORED_DIRS = {
    VENV_DIR,
    ".git",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "site",
    ".gemini",
    "cortex_hive_ui",
}

# Protocol Weights
WEIGHTS = {
    "integrity": 15,
    "architecture": 15,
    "security": 10,
    "complexity": 10,
    "performance": 10,
    "error_handling": 8,
    "duplication": 7,
    "dead_code": 5,
    "testing": 5,
    "naming": 3,
    "standards": 2,
    "aesthetics": 5,
    "psi": 5,
}

TOTAL_WEIGHT = sum(WEIGHTS.values())


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def iter_files(extensions=None):
    for root, dirs, files in os.walk("."):
        # Modify dirs in-place to skip
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            if extensions and not any(file.endswith(ext) for ext in extensions):
                continue
            yield os.path.join(root, file)


def measure_integrity():
    # Try to run the CLI help as a basic integrity check
    code, _, stderr = run_command(f"{VENV_DIR}/bin/python -m cortex.cli --help")
    if code != 0:
        print(f" Integrity Check Failed: {stderr.strip()[:200]}...")
        return 0.0
    return 1.0


def measure_architecture():
    # Check for files > 300 LOC
    files_over_limit = []
    total_files = 0
    for path in iter_files(extensions=[".py"]):
        total_files += 1
        try:
            with open(path, "r") as f:
                lines = len(f.readlines())
                if lines > 300:
                    files_over_limit.append((path, lines))
        except (OSError, IOError):
            pass

    if not total_files:
        return 1.0

    score = 1.0 - (len(files_over_limit) / total_files)
    # Penalize heavily for god objects
    for f, l in files_over_limit:
        print(f"  Architecture Violation: {f} ({l} LOC)")
        score -= 0.1

    return max(0.0, score)


def measure_security():
    patterns = [r"eval\(", r"innerHTML", r"password\s*=", r"secret\s*=", r"api_key\s*="]
    hits = 0
    for path in iter_files(extensions=[".py", ".js", ".html"]):
        try:
            with open(path, "r") as f:
                content = f.read()
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    for p in patterns:
                        if re.search(p, line, re.IGNORECASE):
                            # False positive filtering
                            if "os.environ" in line or "json()" in line or "auth.create_key" in line:
                                continue
                            if "innerHTML" in line and "school.js" in path: # Trusted static content
                                continue
                            if "innerHTML" in line and "AsciiEffect.js" in path: # Three.js lib
                                continue
                                
                            hits += 1
                            print(f"  Security Risk: {p} in {path}:{i+1}")
        except: pass
    
    score = 1.0 - (hits * 0.1)
    return max(0.0, score)


def _is_complex_line(line, leading_spaces_limit=16):
    """Check if line is too deeply indented."""
    leading_spaces = len(line) - len(line.lstrip())
    return leading_spaces > leading_spaces_limit


def measure_complexity():
    # Indentation > 4, functions > 50 LOC
    complexity_hits = 0
    for path in iter_files(extensions=[".py"]):
        try:
            with open(path, "r") as f:
                lines = f.readlines()
                current_func_lines = 0
                in_func = False

                for line in lines:
                    # Indentation check (approximate)
                    if _is_complex_line(line):
                        complexity_hits += 1

                    # Function length check
                    stripped = line.strip()
                    if stripped.startswith("def "):
                        in_func = True
                        current_func_lines = 0
                    elif in_func and stripped:
                        current_func_lines += 1
                        if current_func_lines > 50:
                            complexity_hits += 1
                            in_func = False
        except (OSError, IOError):
            pass

    score = 1.0 - (complexity_hits * 0.05)
    return max(0.0, score)


def measure_psi():
    # grep -rE 'HACK|FIXME|WTF|stupid|TODO|TEMPORARY|WORKAROUND'
    psi_terms = ["HACK", "FIXME", "WTF", "stupid", "TODO", "TEMPORARY", "WORKAROUND"]
    hits = 0
    for path in iter_files(extensions=[".py", ".md", ".txt"]):
        try:
            with open(path, "r") as f:
                content = f.read()
                for term in psi_terms:
                    count = content.count(term)
                    if count > 0:
                        hits += count
                        # print(f"  Psi Hit: {term} in {path}")
        except (OSError, IOError):
            pass

    print(f"  Psi Markers found: {hits}")
    score = 1.0 - (hits * 0.01)  # Small penalty per item, but accumulates
    return max(0.0, score)


def measure_testing():
    test_files = 0
    code_files = 0
    for path in iter_files(extensions=[".py"]):
        code_files += 1
        if "test" in path:
            test_files += 1

    if code_files == 0:
        return 1.0
    ratio = test_files / code_files
    print(f"  Test Ratio: {ratio:.2f}")

    return min(1.0, ratio * 2)


def main():
    print("running X-Ray 13D...")

    scores = {}
    with ThreadPoolExecutor() as executor:
        f_int = executor.submit(measure_integrity)
        f_arch = executor.submit(measure_architecture)
        f_sec = executor.submit(measure_security)
        f_comp = executor.submit(measure_complexity)
        f_psi = executor.submit(measure_psi)
        f_test = executor.submit(measure_testing)

        scores["integrity"] = f_int.result()
        scores["architecture"] = f_arch.result()
        scores["security"] = f_sec.result()
        scores["complexity"] = f_comp.result()
        scores["psi"] = f_psi.result()
        scores["testing"] = f_test.result()

    # Default others to 0.5 (middle ground) or estimated
    scores["performance"] = 0.5
    scores["error_handling"] = 0.5
    scores["duplication"] = 0.5
    scores["dead_code"] = 0.5
    scores["naming"] = 0.7
    scores["standards"] = 0.7
    scores["aesthetics"] = 0.7

    total_score = 0
    for dim, weight in WEIGHTS.items():
        s = scores.get(dim, 0.5)
        total_score += s * weight
        print(f"{dim.capitalize()}: {s:.2f} (Weight: {weight})")

    final_score = (total_score / TOTAL_WEIGHT) * 100
    print(f"\n⚡ FINAL SCORE: {final_score:.2f}/100")

    if final_score < 30:
        print("☢️  STATUS: REWRITE TOTAL")
    elif final_score < 50:
        print("☣️  STATUS: BRUTAL MODE")
    elif final_score < 70:
        print("🛠️  STATUS: MEJORAlo STANDARD")
    else:
        print("✨ STATUS: POLISH")


if __name__ == "__main__":
    main()
