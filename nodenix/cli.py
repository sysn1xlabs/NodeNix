"""Command-line interface with explicit collection and export failure handling."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

from . import __version__, default_output
from .engine import analyze
from .report import build_report
from .validation import load_scan

ROOT = Path(__file__).resolve().parents[1]

class CollectionError(RuntimeError):
    """Windows collection could not produce a usable snapshot."""


def _is_windows():
    return os.name == 'nt'


def prepare_output(output):
    """Fail before a long scan if the destination cannot accept files."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=output) as probe:
        probe.write(b'NodeNix write check')
        probe.flush()
    return output


def collect_scan(connectivity=False, event_hours=24, timeout=300):
    if not _is_windows():
        raise CollectionError('Live collection requires Windows. Use "demo" or "report" on this computer.')
    powershell = shutil.which('powershell.exe') or shutil.which('pwsh.exe')
    if not powershell:
        raise CollectionError('PowerShell was not found. Windows PowerShell 5.1 or PowerShell 7 is required.')
    script = ROOT / 'collector' / 'Collect-NodeNix.ps1'
    if not script.is_file():
        raise CollectionError('Collector script is missing. Extract the entire NodeNix release, not only nodenix.py.')
    with tempfile.TemporaryDirectory(prefix='nodenix-') as temp:
        raw = Path(temp) / 'scan.json'
        cmd = [powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
               '-OutputPath', str(raw), '-EventHours', str(event_hours)]
        if connectivity:
            cmd.append('-Connectivity')
        print(f'Collecting Windows evidence (maximum {timeout}s)...', flush=True)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, errors='replace', timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise CollectionError(f'Collection exceeded {timeout}s and was stopped. No report was generated. Retry or increase --scan-timeout.') from exc
        if result.stdout:
            print(result.stdout.rstrip())
        if result.returncode:
            detail = (result.stderr or result.stdout or 'No PowerShell error details were returned.').strip()
            lowered = detail.casefold()
            if 'running scripts is disabled' in lowered or 'pssecurityexception' in lowered:
                hint = 'PowerShell policy blocked collection. NodeNix already sets a process-only override; run Get-ExecutionPolicy -List to check organization policy.'
            elif 'could not write' in lowered or 'access is denied' in lowered:
                hint = 'PowerShell could not write its temporary scan. Check the folder and Windows Security Protection History; keep Defender enabled.'
            else:
                hint = f'Windows collector exited with code {result.returncode}. Review the details below; unavailable individual checks normally do not stop a scan.'
            raise CollectionError(f'{hint}\n{detail[-2000:]}')
        if not raw.is_file():
            raise CollectionError('Collector completed but did not create Scan.json. Check write permissions and Protection History.')
        return load_scan(raw)


def _positive_timeout(value):
    number = int(value)
    if not 1 <= number <= 3600:
        raise argparse.ArgumentTypeError('scan timeout must be between 1 and 3600 seconds')
    return number


def parser():
    cli = argparse.ArgumentParser(description='NodeNix — diagnose, resolve, verify. Local Windows diagnostics and portable reports.')
    cli.add_argument('--version', action='version', version=f'NodeNix {__version__}')
    cli.add_argument('--debug', action='store_true', help='Show a traceback for a failed operation (may include local paths)')
    sub = cli.add_subparsers(dest='command', required=True)
    for name in ('demo', 'scan', 'report'):
        p = sub.add_parser(name)
        if name == 'report':
            p.add_argument('input', type=Path)
        p.add_argument('--out', type=Path, default=default_output(name), help='Output folder; default is the OS temp folder / NodeNix / command')
        p.add_argument('--profile', choices=('local', 'share'), default='share' if name == 'report' else 'local')
        p.add_argument('--open', action='store_true', help='Open the HTML report in the default browser')
        if name == 'scan':
            p.add_argument('--connectivity', action='store_true', help='Send ICMP, DNS and HTTPS probes')
            p.add_argument('--event-hours', type=int, choices=range(1, 169), metavar='1..168', default=24)
            p.add_argument('--scan-timeout', type=_positive_timeout, default=300, metavar='SECONDS')
    p = sub.add_parser('compare', help='Compare findings; disappearance is not proof of resolution')
    p.add_argument('before', type=Path)
    p.add_argument('after', type=Path)
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'compare':
            before_scan, after_scan = load_scan(args.before), load_scan(args.after)
            key = lambda finding: (finding['code'], finding['title'])
            old, new = {key(f) for f in analyze(before_scan)}, {key(f) for f in analyze(after_scan)}
            coverage = {}
            for name in sorted(before_scan['sections'].keys() | after_scan['sections'].keys()):
                before = before_scan['sections'].get(name, {}).get('status', 'missing')
                after = after_scan['sections'].get(name, {}).get('status', 'missing')
                if before != after:
                    coverage[name] = {'before': before, 'after': after}
            print(json.dumps({
                'no_longer_observed': sorted(old - new), 'newly_observed': sorted(new - old),
                'still_observed': sorted(old & new), 'coverage_changes': coverage,
                'note': 'Missing or omitted evidence may hide findings. Reproduce the original user issue to verify resolution.',
            }, indent=2))
            return 0
        if args.command == 'demo':
            scan = load_scan(ROOT / 'samples' / 'DemoScan.json')
        elif args.command == 'report':
            if args.input.resolve() == (args.out / 'Scan.json').resolve():
                raise ValueError('Output would overwrite the input scan. Choose a different --out folder, especially for a share report.')
            scan = load_scan(args.input)
        output = prepare_output(args.out)
        if args.command == 'scan':
            scan = collect_scan(args.connectivity, args.event_hours, args.scan_timeout)
        report, bundle, findings = build_report(scan, output, args.profile)
        sections = scan['sections']
        unavailable = sum(s.get('status') == 'unavailable' for s in sections.values())
        print(f'NodeNix {__version__} · {scan["mode"]} · {len(findings)} findings · {args.profile} profile')
        if unavailable:
            print(f'{unavailable} collection section(s) unavailable. Inspect Evidence; unavailable is not a pass.')
        print(f'Report: {report.resolve()}\nBundle: {bundle.resolve()}')
        if args.profile == 'local':
            print('Local exports contain endpoint identifiers. Use a separate share-profile report before sharing.')
        if args.open:
            try:
                if not webbrowser.open(report.resolve().as_uri()):
                    print('Browser did not open. Open Report.html manually; the exports were saved.')
            except OSError:
                print('Browser could not open. Open Report.html manually; the exports were saved.')
        return 0
    except KeyboardInterrupt:
        print('NodeNix: interrupted. No resolution is assumed; incomplete exports should be discarded.', file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, KeyError, CollectionError, subprocess.SubprocessError) as exc:
        if args.debug:
            import traceback
            traceback.print_exc()
        elif isinstance(exc, PermissionError):
            print('NodeNix: access was blocked while reading or writing a file. Use a writable --out folder under %TEMP% and check Protection History.', file=sys.stderr)
        elif isinstance(exc, FileNotFoundError):
            print(f'NodeNix: required file or program was not found: {exc.filename or exc}. Extract the full project and check the supplied path.', file=sys.stderr)
        else:
            print(f'NodeNix: {exc}', file=sys.stderr)
        return 1
