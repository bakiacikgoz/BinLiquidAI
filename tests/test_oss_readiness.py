from pathlib import Path

from scripts.check_oss_readiness import check_repository


def test_repository_oss_readiness_passes() -> None:
    assert check_repository(Path(".")) == []


def test_missing_license_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# ImperaOS\n", encoding="utf-8")
    errors = check_repository(tmp_path)
    assert any("LICENSE" in error for error in errors)
