"""Minimal server-side authentication for mutating harness actions."""

from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException


def require_reviewer(authorization: Optional[str] = Header(default=None)) -> str:
    """Authenticate an approval request and return the configured reviewer ID.

    Args:
        authorization: Bearer token supplied by the trusted frontend or agent.

    Returns:
        Reviewer identity configured by `HARNESS_REVIEWER_ID`.

    Raises:
        HTTPException: 401 for missing or invalid credentials, or 503 when the
            approval token has not been configured.
    """
    expected_token: str = os.getenv("HARNESS_APPROVAL_TOKEN", "")
    if not expected_token:
        raise HTTPException(status_code=503, detail="approval authentication is not configured")
    scheme: str
    separator: str
    supplied_token: str
    scheme, separator, supplied_token = (authorization or "").partition(" ")
    if (
        scheme.lower() != "bearer"
        or not separator
        or not hmac.compare_digest(supplied_token, expected_token)
    ):
        raise HTTPException(status_code=401, detail="valid bearer credentials are required")
    return os.getenv("HARNESS_REVIEWER_ID", "configured-reviewer")
