import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from nodenix.engine import analyze
from nodenix.privacy import share_scan
from nodenix.report import build_report
from nodenix import __version__
from nodenix import default_output

ROOT=Path(__file__).resolve().parents[1]
class NodeNixTests(unittest.TestCase):
    def setUp(self):self.scan=json.loads((ROOT/'samples/DemoScan.json').read_text())
    def test_version_and_default_output(self):
        self.assertEqual(__version__,'0.1.2')
        self.assertEqual(default_output('scan'),Path(tempfile.gettempdir())/'NodeNix'/'scan')
    def test_demo_findings(self):
        codes={f['code'] for f in analyze(self.scan)}
        self.assertTrue({'DISK_SPACE','DNS_FAILED','SPOOLER_STOPPED','DEVICE_ERROR'}<=codes)
        self.assertNotIn('BITLOCKER_OFF',codes)
    def test_missing_security_never_passes_or_fails(self):
        self.scan['sections']['defender']={'status':'unavailable','data':None}
        self.assertFalse(any(f['code'].startswith('DEFENDER') for f in analyze(self.scan)))
    def test_icmp_failure_is_not_dns_fault(self):
        self.scan['sections']['connectivity']['data'].update(dns=True,https=True,gateway=False,internet_icmp=False)
        network=[f for f in analyze(self.scan) if f['category']=='Network']
        self.assertEqual([f['code'] for f in network],['ICMP_FAILED'])
        self.assertEqual(network[0]['severity'],'info')
    def test_event_provider_required(self):
        self.scan['sections']['events']['data']['events']=[{'Id':41,'ProviderName':'Unrelated'}]
        self.assertNotIn('UNEXPECTED_SHUTDOWN',{f['code'] for f in analyze(self.scan)})
    def test_share_profile_whitelist(self):
        original=deepcopy(self.scan)
        self.scan['sections']['system']['data']['future_secret']='secret-token'
        shared=share_scan(self.scan);raw=json.dumps(shared)
        for sensitive in ['LAB-DESKTOP-01','demo-technician','DEMO-ONLY','192.0.2.20','198.51.100.10','secret-token']:
            self.assertNotIn(sensitive,raw)
        self.assertEqual(shared['sections']['network']['status'],'omitted')
        self.assertEqual(self.scan['sections']['system']['data']['hostname'],original['sections']['system']['data']['hostname'])
    def test_error_detail_removed_in_share(self):
        self.scan['sections']['bitlocker']['error']='C:\\Users\\PrivateName\\secret'
        self.assertNotIn('PrivateName',json.dumps(share_scan(self.scan)))
    def test_script_tag_escape(self):
        self.scan['sections']['system']['data']['hostname']='</script><script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as t:
            report,_,_=build_report(self.scan,t,'local')
            html=report.read_text()
            self.assertNotIn('</script><script>alert(1)',html)
            self.assertIn('\\u003c/script',html)
    def test_bundle_manifest_and_no_unrelated_files(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'private.txt').write_text('secret')
            _,bundle,_=build_report(self.scan,t,'share')
            with zipfile.ZipFile(bundle) as z:
                self.assertNotIn('private.txt',z.namelist())
                for line in z.read('Manifest.sha256').decode().splitlines():
                    digest,name=line.split('  ',1)
                    self.assertEqual(digest,hashlib.sha256(z.read(name)).hexdigest())
                self.assertNotIn('LAB-DESKTOP-01',z.read('Report.html').decode())
    def test_csv_formula_injection(self):
        self.scan['sections']['software']['data']=[{'DisplayName':'=HYPERLINK("bad")'}]
        with tempfile.TemporaryDirectory() as t:
            _,bundle,_=build_report(self.scan,t,'local')
            with zipfile.ZipFile(bundle) as z:
                self.assertIn("'=HYPERLINK",z.read('Evidence/software.csv').decode('utf-8-sig'))
    def test_csv_headers_are_neutralized_too(self):
        self.scan['sections']['software']['data']=[{'=2+2':'ordinary value'}]
        with tempfile.TemporaryDirectory() as t:
            _,bundle,_=build_report(self.scan,t,'local')
            with zipfile.ZipFile(bundle) as z:
                self.assertTrue(z.read('Evidence/software.csv').decode('utf-8-sig').startswith("'=2+2"))
    def test_imported_section_cannot_escape_archive(self):
        self.scan['sections']['../../bad']={'status':'ok','data':[]}
        with tempfile.TemporaryDirectory() as t:
            _,bundle,_=build_report(self.scan,t,'local')
            with zipfile.ZipFile(bundle) as z:self.assertFalse(any('..' in n for n in z.namelist()))
    def test_no_automatic_resolution(self):
        with tempfile.TemporaryDirectory() as t:
            build_report(self.scan,t)
            text=(Path(t)/'Ticket.txt').read_text()
            self.assertIn('Status: Investigating',text)
            self.assertIn('Verification: Not recorded',text)
    def test_scalar_storage_from_powershell(self):
        self.scan['sections']['storage']['data']=self.scan['sections']['storage']['data'][0]
        self.assertIn('DISK_SPACE',{f['code'] for f in analyze(self.scan)})

if __name__=='__main__':unittest.main()
