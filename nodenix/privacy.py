"""Share profile uses a whitelist, not best-effort regex redaction."""
from copy import deepcopy
SAFE = {
 'system': ['os','build','uptime_days','memory_percent','ram_gb','manufacturer','model'],
 'storage':['drive','size_gb','free_gb','used_percent','filesystem'],
 'connectivity':['tested','gateway','internet_icmp','dns','https','target'],
 'defender':['AntivirusEnabled','RealTimeProtectionEnabled','AntivirusSignatureAge','AMServiceEnabled'],
 'firewall':['Name','Enabled'], 'bitlocker':['MountPoint','ProtectionStatus','VolumeStatus'],
 'secure_boot':['enabled'], 'tpm':['TpmPresent','TpmReady'],
}
def share_scan(scan):
    output={k:deepcopy(scan[k]) for k in ('schema_version','version','mode','generated_at','elevated') if k in scan}
    output['privacy']='share'; output['sections']={}
    for name, section in scan.get('sections',{}).items():
        if name not in SAFE:
            output['sections'][name]={'status':'omitted','data':None,'reason':'Excluded from share profile.'}; continue
        if section.get('status') != 'ok':
            output['sections'][name]={'status':'unavailable','data':None,'error':'Collection unavailable; details omitted.'}; continue
        value=section.get('data')
        def pick(item):
            return {k:deepcopy(item[k]) for k in SAFE[name] if k in item} if isinstance(item,dict) else None
        output['sections'][name]={'status':'ok','data':[pick(i) for i in value] if isinstance(value,list) else pick(value)}
    return output
