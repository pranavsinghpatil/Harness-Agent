"""Evidence bundle manifest and cryptographic checksums."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Dict


@dataclass
class EvidenceManifest:
    """Cryptographic manifest anchoring all artifacts in an evidence bundle."""

    bundle_id: str
    case_id: str
    case_digest: str
    created_at: str
    files: Dict[str, str] = field(default_factory=dict)  # relative_path -> sha256
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "case_id": self.case_id,
            "case_digest": self.case_digest,
            "created_at": self.created_at,
            "files": self.files,
            "metadata": self.metadata,
        }

    @classmethod
    def create(
        cls,
        bundle_id: str,
        case_id: str,
        case_digest: str,
        bundle_dir: Path,
        metadata: Dict[str, Any] | None = None,
    ) -> EvidenceManifest:
        """Scan a directory and record SHA-256 hashes for all non-manifest files."""
        files: Dict[str, str] = {}
        for p in bundle_dir.rglob("*"):
            if p.is_file() and p.name != "manifest.json":
                rel = str(p.relative_to(bundle_dir)).replace("\\", "/")
                content = p.read_bytes()
                files[rel] = sha256(content).hexdigest()

        return cls(
            bundle_id=bundle_id,
            case_id=case_id,
            case_digest=case_digest,
            created_at=datetime.now(timezone.utc).isoformat(),
            files=files,
            metadata=metadata or {},
        )
