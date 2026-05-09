#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def replace_or_fail(path: Path, pattern: str, replacement: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text, count=expected, flags=re.MULTILINE)
    if count != expected:
        raise RuntimeError(f"Expected {expected} replacement(s) in {path}, got {count}.")
    path.write_text(new_text, encoding="utf-8")


def read_first(path: Path, pattern: str) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(pattern, text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(f"Unable to read version from {path}.")
    return m.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync release version across runtime metadata files.")
    parser.add_argument("version", help="Semver-like version (e.g., 0.6.1)")
    args = parser.parse_args()

    version = args.version.strip()
    if not SEMVER_PATTERN.match(version):
        raise SystemExit(f"Invalid version: {version}. Expected semver-like format, e.g. 0.6.1")

    root = Path(__file__).resolve().parents[1]
    setup_py = root / "setup.py"
    main_py = root / "main.py"
    cli_js = root / "cli.js"

    replace_or_fail(
        setup_py,
        r'version\s*=\s*"[^"]+"',
        f'version="{version}"',
    )
    replace_or_fail(
        main_py,
        r'version="[^"]+"',
        f'version="{version}"',
    )
    replace_or_fail(
        cli_js,
        r'(\{\s*name:\s*"notemd-mcp",\s*version:\s*")[^"]+("\s*\})',
        rf"\g<1>{version}\g<2>",
    )

    setup_version = read_first(setup_py, r'version\s*=\s*"([^"]+)"')
    main_version = read_first(main_py, r'version="([^"]+)"')
    cli_version = read_first(
        cli_js,
        r'\{\s*name:\s*"notemd-mcp",\s*version:\s*"([^"]+)"\s*\}',
    )

    if len({setup_version, main_version, cli_version}) != 1:
        raise RuntimeError(
            "Version mismatch after update: "
            f"setup.py={setup_version}, main.py={main_version}, cli.js={cli_version}"
        )

    print(f"Synced setup.py, main.py, cli.js to version {version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
