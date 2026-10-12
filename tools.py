"""Filesystem tools the agents use. All paths are sandboxed to the project dir."""
import io
import os
import re
import time
import zipfile
from pathlib import Path

ROOT = Path(os.getenv("OUTPUT_DIR", "generated_projects")).resolve()


def new_project_dir(name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
    path = ROOT / f"{slug}-{time.strftime('%Y%m%d-%H%M%S')}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_path(project_dir: str | Path, rel: str) -> Path:
    base = Path(project_dir).resolve()
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"Path escapes project directory: {rel}")
    return target


def write_file(project_dir: str | Path, rel: str, content: str) -> str:
    target = _safe_path(project_dir, rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target)


def read_file(project_dir: str | Path, rel: str) -> str:
    target = _safe_path(project_dir, rel)
    return target.read_text(encoding="utf-8") if target.exists() else ""


def list_files(project_dir: str | Path) -> list[str]:
    base = Path(project_dir)
    return sorted(
        str(p.relative_to(base)).replace(os.sep, "/")
        for p in base.rglob("*")
        if p.is_file()
    )


def zip_project(project_dir: str | Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in list_files(project_dir):
            zf.write(Path(project_dir) / rel, rel)
    return buf.getvalue()
