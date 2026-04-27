#!/usr/bin/env python3
"""Convert a .pptx to a directory of slide-<N>.jpg images.

Usage:
  pptx_to_images.py <deck.pptx> [out_dir] [--dpi 120]

On success, prints one absolute JPEG path per slide (one per line) on stdout,
so the calling shell / agent can feed them directly into a visual-QA step
(e.g. load them in the browser tool, iterate with `for f in $(...); do ...`).

Pipeline: LibreOffice (headless) converts the .pptx to PDF, then
`pdftoppm` rasterises each PDF page to a JPEG. Both tools are preinstalled
in the harness image.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _which_or_die(name: str) -> str:
    path = shutil.which(name)
    if not path:
        print(f"error: required binary '{name}' not found in PATH", file=sys.stderr)
        sys.exit(3)
    return path


def convert(pptx: Path, out_dir: Path, dpi: int) -> list[Path]:
    if not pptx.exists():
        print(f"error: not found: {pptx}", file=sys.stderr)
        sys.exit(1)
    if pptx.suffix.lower() != ".pptx":
        print(f"error: expected .pptx, got {pptx.suffix}", file=sys.stderr)
        sys.exit(1)

    soffice = _which_or_die("libreoffice")
    pdftoppm = _which_or_die("pdftoppm")

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("slide-*.jpg"):
        old.unlink()

    with tempfile.TemporaryDirectory(prefix="pptx2img-") as tmp:
        tmp_path = Path(tmp)
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_path),
                str(pptx),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "HOME": tmp},
        )

        pdf_path = tmp_path / (pptx.stem + ".pdf")
        if not pdf_path.exists():
            matches = list(tmp_path.glob("*.pdf"))
            if not matches:
                print("error: libreoffice produced no PDF", file=sys.stderr)
                sys.exit(4)
            pdf_path = matches[0]

        subprocess.run(
            [
                pdftoppm,
                "-jpeg",
                "-r",
                str(dpi),
                str(pdf_path),
                str(out_dir / "slide"),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    images = sorted(out_dir.glob("slide-*.jpg"))
    if not images:
        print("error: pdftoppm produced no JPEGs", file=sys.stderr)
        sys.exit(5)
    return images


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx", type=Path)
    ap.add_argument(
        "out_dir",
        type=Path,
        nargs="?",
        default=Path("/tmp/pptx-qa"),
        help="output dir for slide-<N>.jpg (default: /tmp/pptx-qa)",
    )
    ap.add_argument("--dpi", type=int, default=120)
    args = ap.parse_args()

    images = convert(args.pptx, args.out_dir, args.dpi)
    for img in images:
        print(img)


if __name__ == "__main__":
    main()
