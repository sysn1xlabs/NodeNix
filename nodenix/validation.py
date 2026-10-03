"""Validate scan imports before they reach analysis, HTML or CSV generation."""
import json
import math
from pathlib import Path

MAX_SCAN_BYTES = 25 * 1024 * 1024
OBJECT_SECTIONS = {
    'system', 'hardware', 'connectivity', 'printers', 'events', 'updates',
    'defender', 'secure_boot', 'tpm',
}

class ScanValidationError(ValueError):
    """A scan cannot be interpreted safely by schema 1 readers."""


def _error(location, expected):
    raise ScanValidationError(f'Invalid scan at {location}: expected {expected}.')


def _records(value, location):
    if value is None:
        return
    items = value if isinstance(value, list) else [value]
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            _error(f'{location}[{index}]', 'an object record')


def _number(obj, key, location, minimum=0, maximum=None):
    value = obj.get(key)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _error(f'{location}.{key}', 'a finite number or null')
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        _error(f'{location}.{key}', f'a number >= {minimum}' + (f' and <= {maximum}' if maximum is not None else ''))


def _bool(obj, key, location):
    if obj.get(key) is not None and not isinstance(obj[key], bool):
        _error(f'{location}.{key}', 'true, false or null')


def _string(obj, key, location):
    if obj.get(key) is not None and not isinstance(obj[key], str):
        _error(f'{location}.{key}', 'text or null')


def _finite_tree(value, location='scan', depth=0):
    if depth > 40:
        _error(location, 'at most 40 levels of nesting')
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            _error(location, 'a finite JSON number representable by the report engine')
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _error(location, 'text object keys')
            _finite_tree(child, f'{location}.{key}', depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _finite_tree(child, f'{location}[{index}]', depth + 1)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        _error(location, 'a JSON value')


def validate_scan(scan):
    if not isinstance(scan, dict):
        _error('scan', 'a NodeNix JSON object')
    if type(scan.get('schema_version')) is not int or scan['schema_version'] != 1:
        _error('schema_version', 'schema version 1')
    if not isinstance(scan.get('sections'), dict):
        _error('sections', 'an object of collection sections')
    if scan.get('mode') not in ('demo', 'live'):
        _error('mode', 'demo or live')
    _string(scan, 'version', 'scan')
    _string(scan, 'generated_at', 'scan')
    _bool(scan, 'elevated', 'scan')
    _finite_tree(scan)
    for name, section in scan['sections'].items():
        location = f'sections.{name}'
        if not isinstance(section, dict) or section.get('status') not in ('ok', 'unavailable', 'omitted'):
            _error(location, 'a section with status ok, unavailable or omitted')
        for key in ('error', 'reason'):
            _string(section, key, location)
        if section['status'] != 'ok':
            continue
        content = section.get('data')
        if name in OBJECT_SECTIONS and not isinstance(content, dict):
            _error(f'{location}.data', 'an object (mark unavailable when no data exists)')
        if name not in OBJECT_SECTIONS:
            _records(content, f'{location}.data')
        if name == 'system':
            for key in ('uptime_days', 'ram_gb'):
                _number(content, key, location)
            _number(content, 'memory_percent', location, maximum=100)
            for key in ('hostname', 'user', 'os', 'build', 'manufacturer', 'model', 'serial', 'bios', 'domain'):
                _string(content, key, location)
        elif name == 'storage':
            for disk in content if isinstance(content, list) else ([content] if content else []):
                for key in ('size_gb', 'free_gb'):
                    _number(disk, key, location)
                _number(disk, 'used_percent', location, maximum=100)
                _string(disk, 'drive', location)
        elif name == 'hardware':
            for key in ('cpu', 'gpu', 'battery', 'devices'):
                _records(content.get(key), f'{location}.{key}')
        elif name == 'printers':
            for key in ('printers', 'jobs'):
                _records(content.get(key), f'{location}.{key}')
            _string(content, 'spooler', location)
        elif name == 'events':
            _records(content.get('events'), f'{location}.events')
            _number(content, 'hours', location)
            events = content.get('events')
            for event in events if isinstance(events, list) else ([events] if events else []):
                _number(event, 'Id', location)
                _string(event, 'ProviderName', location)
        elif name == 'updates':
            _records(content.get('hotfixes'), f'{location}.hotfixes')
            _bool(content, 'reboot_pending', location)
        elif name == 'connectivity':
            for key in ('tested', 'gateway', 'internet_icmp', 'dns', 'https'):
                _bool(content, key, location)
            _string(content, 'target', location)
        elif name == 'defender':
            for key in ('AntivirusEnabled', 'RealTimeProtectionEnabled', 'AMServiceEnabled'):
                _bool(content, key, location)
            _number(content, 'AntivirusSignatureAge', location)
        elif name == 'secure_boot':
            _bool(content, 'enabled', location)
        elif name == 'tpm':
            for key in ('TpmPresent', 'TpmReady'):
                _bool(content, key, location)
    return scan


def load_scan(path):
    path = Path(path)
    if path.stat().st_size > MAX_SCAN_BYTES:
        raise ScanValidationError('Scan exceeds the 25 MB import limit.')
    raw = path.read_bytes()
    if len(raw) > MAX_SCAN_BYTES:
        raise ScanValidationError('Scan exceeds the 25 MB import limit.')
    try:
        scan = json.loads(raw.decode('utf-8-sig'), parse_constant=lambda value: _error(value, 'a finite JSON number'))
    except UnicodeDecodeError as exc:
        raise ScanValidationError('Scan must be UTF-8 JSON; export again from the NodeNix collector.') from exc
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ScanValidationError(f'Scan is not readable JSON: {exc}') from exc
    return validate_scan(scan)
