import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path


CONVERSION_DIR_RE = re.compile(r"^[a-f0-9]{32}$")


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True)
class TempStoragePolicy:
    retention_seconds: int = 24 * 60 * 60
    max_conversion_directories: int = 200
    max_total_bytes: int = 2 * 1024 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "TempStoragePolicy":
        return cls(
            retention_seconds=_env_int("WORD2JATS_TEMP_RETENTION_HOURS", 24) * 3600,
            max_conversion_directories=_env_int("WORD2JATS_MAX_TEMP_JOBS", 200),
            max_total_bytes=_env_int("WORD2JATS_MAX_TEMP_GB", 2) * 1024**3,
        )


class TempStorageManager:
    """Opportunistically remove expired conversion media without touching other paths."""

    def __init__(self, root: str | Path, policy: TempStoragePolicy | None = None):
        self.root = Path(root).resolve()
        self.policy = policy or TempStoragePolicy.from_env()

    def cleanup(self, exclude: set[str] | None = None) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        excluded = exclude or set()
        now = time.time()
        jobs = []
        for path in self.root.iterdir():
            if (
                not path.is_dir()
                or not CONVERSION_DIR_RE.fullmatch(path.name)
                or path.name in excluded
            ):
                continue
            try:
                modified = path.stat().st_mtime
                size = self._directory_size(path)
            except OSError:
                continue
            jobs.append((path, modified, size))

        removed = 0
        retained = []
        for path, modified, size in jobs:
            if now - modified > self.policy.retention_seconds:
                removed += self.remove(path)
            else:
                retained.append((path, modified, size))

        retained.sort(key=lambda item: item[1], reverse=True)
        total = 0
        for index, (path, _, size) in enumerate(retained):
            keep = (
                index < self.policy.max_conversion_directories
                and total + size <= self.policy.max_total_bytes
            )
            if keep:
                total += size
            else:
                removed += self.remove(path)
        return removed

    def remove(self, path: str | Path) -> int:
        candidate = Path(path).resolve()
        if (
            candidate.parent != self.root
            or not CONVERSION_DIR_RE.fullmatch(candidate.name)
            or not candidate.exists()
        ):
            return 0
        try:
            shutil.rmtree(candidate)
            return 1
        except OSError:
            return 0

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                continue
        return total

