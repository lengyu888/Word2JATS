"""Repository-level release gate for the reproducible demo package.

This check is intentionally dependency-free so it can run before installing
the backend or frontend. It validates the files that make the official demo
reproducible and prevents stale claims or local-only deliverables from being
committed accidentally.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


STALE_PHRASES = (
    "尚未接入正式 DTD/XSD 校验",
    "当前不包含正式 DTD/XSD 校验",
    "参考文献尚未进一步拆分",
)

FORBIDDEN_TRACKED = (
    "JATSv1.3 完整手册.pdf",
    "docs/Word2JATS技术方案说明书.docx",
    "docs/Word2JATS技术方案说明书.pdf",
    "release/word2jats-docker-images.tar",
    "release/word2jats-docker-images.zip",
    "scripts/generate_technical_solution_docx.py",
    "scripts/generate_technical_solution_pdf.py",
)


def collect_release_issues(root: Path | None = None) -> list[str]:
    repo = (root or Path(__file__).resolve().parents[2]).resolve()
    issues: list[str] = []

    required = (
        "README.md",
        "backend/README.md",
        "frontend/README.md",
        "docker-compose.yml",
        "backend/app/main.py",
        "backend/evaluate_official_samples.py",
        "backend/schemas/JATS-Publishing-1-3-MathML3-DTD/JATS-journalpublishing1-3-mathml3.dtd",
        "frontend/package.json",
        "frontend/package-lock.json",
    )
    for relative in required:
        if not (repo / relative).is_file():
            issues.append(f"缺少发布必需文件：{relative}")

    for readme in (repo / "README.md", repo / "backend/README.md", repo / "frontend/README.md"):
        if not readme.is_file():
            continue
        content = readme.read_text(encoding="utf-8")
        for phrase in STALE_PHRASES:
            if phrase in content:
                issues.append(f"{readme.relative_to(repo)} 含旧限制表述：{phrase}")

    tracked = _tracked_paths(repo)
    for relative in FORBIDDEN_TRACKED:
        if relative in tracked:
            issues.append(f"不应提交的本地交付物已被 Git 跟踪：{relative}")
    return issues


def _tracked_paths(repo: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def main() -> int:
    issues = collect_release_issues()
    if issues:
        print("RELEASE CHECK FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("RELEASE CHECK PASSED")
    print("- Official sample evaluator: ready")
    print("- Local JATS 1.3 MathML3 DTD: ready")
    print("- Docker and frontend entry points: ready")
    print("- Excluded local deliverables: not tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
