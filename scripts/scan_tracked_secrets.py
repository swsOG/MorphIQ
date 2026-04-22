import re
import subprocess
import sys
from pathlib import Path


PATTERNS = {
    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "anthropic_key": re.compile(r"sk-ant-[0-9A-Za-z\-_]+"),
    "generic_secret_assignment": re.compile(r"(API_KEY|SECRET_KEY|TOKEN)\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
}

ALLOWLIST = {
    ".env.example",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    hits: list[str] = []
    for rel_path in tracked_files():
        if rel_path.name in ALLOWLIST:
            continue
        try:
            text = rel_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                hits.append(f"{rel_path}:{label}:{match.group(0)[:80]}")
    if hits:
        print("Potential secrets found in tracked files:")
        for hit in hits:
            print(f" - {hit}")
        return 1
    print("No obvious secrets found in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
