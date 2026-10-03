import csv
import hashlib
import io
import json
import zipfile
import tempfile
from pathlib import Path
from .engine import analyze, WORKFLOWS
from .privacy import share_scan
from .validation import validate_scan
from . import __version__

def build_report(scan, output, profile='share'):
    if profile not in ('share', 'local'):
        raise ValueError('Report profile must be local or share.')
    validate_scan(scan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Build everything in a private staging folder first. A generation failure
    # leaves the prior export files intact. Individual final file moves are atomic.
    with tempfile.TemporaryDirectory(prefix='.nodenix-', dir=output) as staging:
        report, bundle, findings = _build_report(scan, Path(staging), profile)
        for name in ('Scan.json', 'Findings.json', 'Ticket.txt', bundle.name, report.name):
            (Path(staging) / name).replace(output / name)
    return output / 'Report.html', output / 'NodeNix-SupportBundle.zip', findings


def _build_report(scan, output, profile):
    scan=share_scan(scan) if profile=='share' else dict(scan,privacy='local')
    findings=analyze(scan)
    payload=dict(scan=scan,findings=findings,workflows=WORKFLOWS)
    # Prevent a collected value from breaking out of the JSON script tag.
    embedded=json.dumps(payload,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8')
    (output/'Report.html').write_text(template.replace('__VERSION__',__version__).replace('__PAYLOAD__',embedded),encoding='utf-8')
    (output/'Scan.json').write_text(json.dumps(scan,indent=2),encoding='utf-8')
    (output/'Findings.json').write_text(json.dumps(findings,indent=2),encoding='utf-8')
    lines=[f'NodeNix {__version__} — Investigation notes',f"Mode: {scan.get('mode')}",f"Collected: {scan.get('generated_at')}",f"Profile: {profile}",'Status: Investigating','Root cause: Not established','Action taken: None recorded','Verification: Not recorded','','Diagnostic evidence:']
    lines.extend(f"- [{f['severity']}] {f['title']}: {f['evidence']}" for f in findings)
    (output/'Ticket.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Dedicated clean payload directory means ZIP never sweeps unrelated output files.
    exports={'Report.html':(output/'Report.html').read_bytes(),'Scan.json':(output/'Scan.json').read_bytes(),'Findings.json':(output/'Findings.json').read_bytes(),'Ticket.txt':(output/'Ticket.txt').read_bytes()}
    for name, section in scan.get('sections',{}).items():
        # Imported section keys are never used as paths.
        safe_name=''.join(c for c in name if c.isascii() and (c.isalnum() or c=='_'))[:64]
        if not safe_name or safe_name != name:
            continue
        exports[f'Evidence/{safe_name}.json']=json.dumps(section,indent=2).encode()
        value=section.get('data')
        if isinstance(value,list) and value and all(isinstance(i,dict) for i in value):
            fields=sorted(set().union(*(i.keys() for i in value)))
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields)
            # Neutralize formula-like values when opened in spreadsheet software.
            def cell(v):
                text=json.dumps(v) if isinstance(v,(list,dict)) else str(v if v is not None else '')
                return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
            writer.writerow({key:cell(key) for key in fields})
            writer.writerows({k:cell(v) for k,v in item.items()} for item in value)
            exports[f'Evidence/{safe_name}.csv']=stream.getvalue().encode('utf-8-sig')
    exports['Manifest.sha256']=''.join(f'{hashlib.sha256(value).hexdigest()}  {name}\n' for name,value in exports.items()).encode()
    bundle=output/'NodeNix-SupportBundle.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,value in exports.items(): archive.writestr(name,value)
    return output/'Report.html', bundle, findings
