from pathlib import Path

import imperaos_computer_use


def test_canonical_extension_identity_surfaces() -> None:
    root = Path(imperaos_computer_use.__file__).parent
    expected = {
        "adapters/browser_adapter.py": ['"User-Agent": "ImperaOS/real-acceptance"'],
        "runtime.py": ["Run ImperaOS computer-use on a macOS pilot machine."],
        "vision_runtime/qualification.py": [
            "I understand ImperaOS will control my macOS desktop",
            "<title>ImperaOS Local Fixture</title>",
        ],
    }
    for relative, fragments in expected.items():
        source = (root / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in source
