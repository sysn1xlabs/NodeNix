#!/usr/bin/env python3
"""Guard public source/sample files against accidentally included live evidence."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    'README.md', 'LICENSE', 'CHANGELOG.md', 'QUICKSTART.txt', 'CONTRIBUTING.md',
    'SECURITY.md', 'Start-NodeNix.ps1', 'nodenix.py', '.gitignore',
    '.gitattributes', '.editorconfig',
}
SOURCE_DIRS = {'collector', 'nodenix', 'tests', 'docs', 'scripts', '.github', 'samples'}
SUFFIXES = {'.py', '.ps1', '.md', '.txt', '.json', '.html', '.cjs', '.svg', '.yml', '.yaml'}
SAMPLE_REPORTS = {'samples/DemoReport/Report.html', 'samples/ShareReport/Report.html'}
RUNTIME_NAMES = {'Scan.json', 'Findings.json', 'Ticket.txt', 'Report.html', 'NodeNix-SupportBundle.zip', 'repairs.jsonl'}


def source_files(root=ROOT):
    root = Path(root)
    selected = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or '.git' in relative.parts:
            continue
        name = relative.as_posix()
        if len(relative.parts) == 1 and name in ROOT_FILES:
            selected.append(path)
        elif relative.parts[0] in SOURCE_DIRS and path.suffix in SUFFIXES:
            if path.name in RUNTIME_NAMES and name not in SAMPLE_REPORTS:
                continue
            selected.append(path)
    return sorted(selected)


def candidate_files(root=ROOT):
    root = Path(root)
    if (root / '.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], capture_output=True)
        if result.returncode:
            raise ValueError('Git could not enumerate publishable files. Check repository access.')
        return [root / name for name in result.stdout.decode('utf-8').split('\0') if name and (root / name).is_file()]
    return source_files(root)


def check_files(paths, root=ROOT):
    errors = []
    root = Path(root)
    for path in paths:
        path = Path(path)
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            errors.append(f'{name}: symlinks are not accepted in the release source tree')
            continue
        if path.name in RUNTIME_NAMES and name not in SAMPLE_REPORTS:
            errors.append(f'{name}: generated runtime evidence must not be published')
        if path.name.startswith('.env') or path.suffix in ('.pem', '.key'):
            errors.append(f'{name}: local credential/configuration file must not be published')
        if path.suffix == '.json':
            try:
                value = json.loads(path.read_text(encoding='utf-8-sig'))
            except (ValueError, UnicodeError) as exc:
                errors.append(f'{name}: invalid JSON ({exc})')
                continue
            if isinstance(value, dict) and ('schema_version' in value or 'sections' in value):
                if value.get('mode') != 'demo':
                    errors.append(f'{name}: only explicitly fictional demo scans may be published')
        elif path.suffix == '.html':
            html = path.read_text(encoding='utf-8')
            match = re.search(r'<script id="payload" type="application/json">([\s\S]*?)</script>', html)
            if match and match.group(1) != '__PAYLOAD__':
                try:
                    payload = json.loads(match.group(1))
                    if payload.get('scan', {}).get('mode') != 'demo':
                        errors.append(f'{name}: HTML contains a non-demo scan')
                except (ValueError, AttributeError):
                    errors.append(f'{name}: invalid report payload')
            if name in SAMPLE_REPORTS and not match:
                errors.append(f'{name}: fictional sample payload is missing')
    if errors:
        raise ValueError('\n'.join(errors))
    return len(paths)


def main():
    try:
        count = check_files(candidate_files())
    except (OSError, ValueError) as exc:
        print(f'Public source check failed:\n{exc}')
        return 1
    print(f'Public source check passed: {count} files; no live scan payloads or known runtime exports.')
    print('This is not a general secret scanner. Review staged changes before publishing.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
