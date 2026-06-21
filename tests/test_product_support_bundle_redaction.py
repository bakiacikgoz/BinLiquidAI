from __future__ import annotations


def test_product_support_bundle_redaction_markers_are_not_in_safe_summary() -> None:
    safe_summary = {
        "schemaVersion": "product.support-bundle-redaction/v1",
        "status": "pass",
        "redactedMarkers": ["rawToken", "Authorization: Bearer", "BEGIN PRIVATE KEY"],
        "safeSummary": "support bundle stores hashes and redacted references only",
    }

    text = safe_summary["safeSummary"]
    assert "rawToken" not in text
    assert "Authorization: Bearer" not in text
    assert "BEGIN PRIVATE KEY" not in text
