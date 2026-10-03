"""Regression tests for actual failure boundaries, without running repairs."""
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from nodenix.cli import main, collect_scan, CollectionError
from nodenix.report import build_report
from nodenix.validation import load_scan, validate_scan, ScanValidationError

ROOT = Path(__file__).resolve().parents[1]

class FailureTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan(ROOT / 'samples' / 'DemoScan.json')

    def call_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_nested_records_fail_before_analysis(self):
        scan = deepcopy(self.scan)
        scan['sections']['hardware']['data']['devices'] = [None]
        with self.assertRaisesRegex(ScanValidationError, 'devices'):
            validate_scan(scan)

    def test_numeric_field_rejects_text_and_bool(self):
        for bad in ('eighteen', True):
            scan = deepcopy(self.scan)
            scan['sections']['system']['data']['uptime_days'] = bad
            with self.assertRaisesRegex(ScanValidationError, 'uptime_days'):
                validate_scan(scan)

    def test_json_nan_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            raw = json.dumps(self.scan).replace('88.6', 'NaN')
            path.write_text(raw, encoding='utf-8')
            with self.assertRaisesRegex(ScanValidationError, 'finite'):
                load_scan(path)

    def test_extremely_large_number_is_a_validation_error(self):
        scan = deepcopy(self.scan)
        scan['sections']['system']['data']['uptime_days'] = 10 ** 1000
        with self.assertRaisesRegex(ScanValidationError, 'finite'):
            validate_scan(scan)

    def test_bad_json_cli_has_no_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'bad.json'
            bad.write_text('{missing', encoding='utf-8')
            code, out, err = self.call_cli(['report', str(bad), '--out', str(Path(temp) / 'report')])
            self.assertEqual(code, 1)
            self.assertNotIn('Traceback', err)
            self.assertIn('not readable JSON', err)
            self.assertNotIn('Report:', out)

    def test_report_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / 'Scan.json'
            raw.write_text(json.dumps(self.scan), encoding='utf-8')
            original = raw.read_bytes()
            code, _, err = self.call_cli(['report', str(raw), '--profile', 'share', '--out', temp])
            self.assertEqual(code, 1)
            self.assertIn('overwrite', err)
            self.assertEqual(raw.read_bytes(), original)

    def test_blocked_output_stops_before_collection(self):
        with patch('nodenix.cli.prepare_output', side_effect=PermissionError('blocked')), patch('nodenix.cli.collect_scan') as collect:
            code, _, err = self.call_cli(['scan'])
        self.assertEqual(code, 1)
        collect.assert_not_called()
        self.assertIn('writable', err)

    def test_timeout_does_not_generate_report(self):
        with patch('nodenix.cli._is_windows', return_value=True), patch('nodenix.cli.shutil.which', return_value='powershell.exe'), patch('nodenix.cli.subprocess.run', side_effect=subprocess.TimeoutExpired('powershell', 1)):
            with self.assertRaisesRegex(CollectionError, 'exceeded 1s'):
                collect_scan(timeout=1)

    def test_policy_failure_is_actionable(self):
        failed = subprocess.CompletedProcess(['powershell'], 1, '', 'running scripts is disabled on this system')
        with patch('nodenix.cli._is_windows', return_value=True), patch('nodenix.cli.shutil.which', return_value='powershell.exe'), patch('nodenix.cli.subprocess.run', return_value=failed):
            with self.assertRaisesRegex(CollectionError, 'Get-ExecutionPolicy -List'):
                collect_scan()

    def test_success_without_scan_file_is_not_success(self):
        empty = subprocess.CompletedProcess(['powershell'], 0, '', '')
        with patch('nodenix.cli._is_windows', return_value=True), patch('nodenix.cli.shutil.which', return_value='powershell.exe'), patch('nodenix.cli.subprocess.run', return_value=empty):
            with self.assertRaisesRegex(CollectionError, 'did not create'):
                collect_scan()

    def test_subprocess_uses_process_policy_and_array_arguments(self):
        def run(cmd, **kwargs):
            self.assertIsInstance(cmd, list)
            self.assertEqual(cmd[cmd.index('-ExecutionPolicy') + 1], 'Bypass')
            raw = Path(cmd[cmd.index('-OutputPath') + 1])
            raw.write_text(json.dumps(self.scan), encoding='utf-8')
            self.assertTrue(kwargs['capture_output'])
            self.assertIn('timeout', kwargs)
            return subprocess.CompletedProcess(cmd, 0, '', '')
        with patch('nodenix.cli._is_windows', return_value=True), patch('nodenix.cli.shutil.which', return_value='powershell.exe'), patch('nodenix.cli.subprocess.run', side_effect=run):
            self.assertEqual(collect_scan()['mode'], 'demo')

    def test_browser_failure_keeps_successful_exports(self):
        with tempfile.TemporaryDirectory() as temp, patch('nodenix.cli.webbrowser.open', return_value=False):
            code, out, _ = self.call_cli(['demo', '--out', temp, '--open'])
            self.assertEqual(code, 0)
            self.assertIn('Open Report.html manually', out)
            self.assertTrue((Path(temp) / 'Report.html').is_file())

    def test_generation_failure_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'Report.html'
            report.write_text('previous report', encoding='utf-8')
            with patch('nodenix.report._build_report', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    build_report(self.scan, temp)
            self.assertEqual(report.read_text(encoding='utf-8'), 'previous report')
            self.assertFalse(any(p.name.startswith('.nodenix-') for p in Path(temp).iterdir()))

    def test_invalid_profile_never_falls_back_to_local(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'profile'):
                build_report(self.scan, temp, 'typo')

    def test_compare_exposes_reduced_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            before, after = Path(temp) / 'before.json', Path(temp) / 'after.json'
            before.write_text(json.dumps(self.scan), encoding='utf-8')
            reduced = deepcopy(self.scan)
            reduced['sections']['hardware'] = {'status': 'unavailable', 'data': None}
            after.write_text(json.dumps(reduced), encoding='utf-8')
            code, out, _ = self.call_cli(['compare', str(before), str(after)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)['coverage_changes']['hardware']['after'], 'unavailable')

if __name__ == '__main__':
    unittest.main()
