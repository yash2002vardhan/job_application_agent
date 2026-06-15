"""Load the user's resume into plain text so the agent can tailor applications."""

from __future__ import annotations

from pathlib import Path


def load_resume(path: str | Path) -> str:
    """Read a resume from a .pdf, .txt, or .md file and return its text."""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Resume not found at: {p}")

    suffix = p.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(p)
    elif suffix in {".txt", ".md", ".markdown"}:
        text = p.read_text(encoding="utf-8")
    else:
        raise ValueError(
            f"Unsupported resume format '{suffix}'. Use .pdf, .txt, or .md."
        )

    text = text.strip()
    if not text:
        raise ValueError(f"Resume at {p} appears to be empty.")
    return text


def _read_pdf(p: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(p))
    return "\n".join((page.extract_text() or "") for page in reader.pages)
