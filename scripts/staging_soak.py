import argparse
import time
from collections import Counter

import requests


def run_soak(base_url: str, duration_seconds: int, token: str) -> dict[str, int]:
    started = time.time()
    counters: Counter[str] = Counter()
    headers = {"Authorization": f"Bearer {token}"}

    while time.time() - started < duration_seconds:
        for path in ["/healthz", "/readyz", "/metrics", "/v1/leads"]:
            response = requests.get(f"{base_url}{path}", headers=headers, timeout=5)
            counters[f"status_{response.status_code}"] += 1
            counters["requests_total"] += 1
        time.sleep(0.2)

    return dict(counters)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a lightweight staging soak loop")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--duration-seconds", type=int, default=600)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    summary = run_soak(args.base_url, args.duration_seconds, args.token)
    print("Soak summary:")
    for key in sorted(summary):
        print(f"{key}: {summary[key]}")

    total = summary.get("requests_total", 1)
    errors = sum(value for key, value in summary.items() if key.startswith("status_5"))
    error_rate = errors / total
    print(f"error_rate={error_rate:.4f}")

    if error_rate > 0.02:
        print("Soak failed: 5xx rate above 2%")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
