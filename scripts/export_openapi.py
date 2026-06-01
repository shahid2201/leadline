import json
from pathlib import Path

from app.main import app


def main() -> None:
    output = Path("docs/openapi.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"OpenAPI exported to {output}")


if __name__ == "__main__":
    main()
