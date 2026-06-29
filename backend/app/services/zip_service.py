"""
zip_service.py
--------------
Creates a ZIP archive from an encrypted output directory.
Streams file-by-file so large batches don't spike memory.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


def create_zip(output_dir: Path, zip_path: Path) -> Path:
    """
    Zip all files in *output_dir* into *zip_path*.

    Parameters
    ----------
    output_dir:
        Directory containing the encrypted PDFs.
    zip_path:
        Destination .zip file path.

    Returns
    -------
    Path
        The created zip file path.

    Raises
    ------
    ValueError
        If *output_dir* contains no files.
    """
    pdf_files = sorted(output_dir.glob("*.pdf"))
    if not pdf_files:
        raise ValueError(f"No encrypted PDFs found in {output_dir}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for pdf in pdf_files:
            zf.write(pdf, arcname=pdf.name)

    return zip_path
