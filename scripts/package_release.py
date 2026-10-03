#!/usr/bin/env python3
"""Package explicit checked source files, excluding .git and runtime evidence."""
import argparse
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nodenix import __version__
from check_public_tree import source_files, check_files


def main():
    cli = argparse.ArgumentParser(description='Build a checked NodeNix source release and checksum.')
    cli.add_argument('--out', type=Path, default=Path(tempfile.gettempdir()) / 'NodeNix' / 'releases' / f'NodeNix-v{__version__}.zip')
    args = cli.parse_args()
    try:
        paths = source_files()
        check_files(paths)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.out, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                archive.write(path, 'NodeNix/' + path.relative_to(ROOT).as_posix())
        with zipfile.ZipFile(args.out) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f'Release archive integrity failed at {bad}')
        digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
        checksum = args.out.with_suffix(args.out.suffix + '.sha256')
        checksum.write_text(f'{digest}  {args.out.name}\n', encoding='ascii')
        print(f'Release: {args.out.resolve()} ({len(paths)} source files)')
        print(f'Checksum: {checksum.resolve()}')
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'Release packaging failed: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
