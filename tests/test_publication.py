import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publication_guard', ROOT / 'scripts' / 'check_public_tree.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class PublicationTests(unittest.TestCase):
    def test_live_scan_is_rejected_even_when_renamed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'notes.json'
            path.write_text(json.dumps({'schema_version': 1, 'mode': 'live', 'sections': {}}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fictional demo'):
                guard.check_files([path], Path(temp))

    def test_non_demo_sample_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'samples' / 'DemoReport' / 'Report.html'
            path.parent.mkdir(parents=True)
            path.write_text('<script id="payload" type="application/json">{"scan":{"mode":"live"}}</script>', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'non-demo'):
                guard.check_files([path], Path(temp))

    def test_source_selection_excludes_runtime_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            (root / 'docs' / 'Report.html').write_text('private export', encoding='utf-8')
            (root / 'README.md').write_text('readme', encoding='utf-8')
            self.assertEqual(guard.source_files(root), [root / 'README.md'])

    def test_real_fictional_samples_pass(self):
        paths = [ROOT / 'samples' / 'DemoScan.json', ROOT / 'samples' / 'DemoReport' / 'Report.html']
        self.assertEqual(guard.check_files(paths), 2)

if __name__ == '__main__':
    unittest.main()
