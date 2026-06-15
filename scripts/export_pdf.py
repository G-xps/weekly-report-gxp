#!/usr/bin/env python3
"""Export an HTML weekly report to PDF with Chrome when available."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def find_chrome() -> str | None:
    candidates = [
        "chrome",
        "google-chrome",
        "chromium",
        "msedge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html_file")
    parser.add_argument("--output")
    args = parser.parse_args()
    html_file = Path(args.html_file).resolve()
    output = Path(args.output).resolve() if args.output else html_file.with_suffix(".pdf")
    chrome = find_chrome()
    if not chrome:
        print("Chrome/Edge not found. Open the HTML file in a browser and use Ctrl+P -> Save as PDF.")
        print(f"HTML file: {html_file}")
        return
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={output}",
        str(html_file),
    ]
    subprocess.run(cmd, check=True)
    print(f"PDF report generated: {output}")


if __name__ == "__main__":
    main()
