import subprocess
import sys

LAYER_MARKERS = [
    "unit",
    "integration",
    "contract",
    "e2e",
    "ai_regression",
]


def main() -> int:
    for marker in LAYER_MARKERS:
        print(f"\n=== Running {marker} tests ===")
        command = [sys.executable, "-m", "pytest", "-m", marker]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
