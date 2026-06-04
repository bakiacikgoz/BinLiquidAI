from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    request_path = Path(__file__).with_suffix(".json")
    print(json.dumps(json.loads(request_path.read_text(encoding="utf-8")), sort_keys=True))


if __name__ == "__main__":
    main()
