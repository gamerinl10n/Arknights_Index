"""Join official display names by stable operator ID, never by translated similarity."""
import json
import subprocess
from pathlib import Path
from languages import LANGUAGES

def update_catalog(root, revision, output):
    catalog = {}
    for lang,folder in LANGUAGES.items():
        raw = subprocess.check_output(['git','-C',str(root),'show',f'{revision}:{folder}/gamedata/excel/character_table.json'],text=True)
        for cid,row in json.loads(raw).items():
            name = row.get('name')
            if name and cid.startswith('char_'):
                catalog.setdefault(cid, {'id':cid,'names':{}})['names'][lang] = [name]
    # Stable operator IDs link translations; search abbreviations remain explicit.
    for row in catalog.values():
        if row['id']=='char_003_kalts': row['aliases']=['kaltsit']
        if any('Mon3tr' in names for names in row['names'].values()): row['aliases']=['M3']
    payload={'source':'ArknightsAssets/ArknightsGamedata','revision':revision}
    Path(output).write_text(json.dumps(list(catalog.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Path(output).with_suffix('.source.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('revision');p.add_argument('--output',default='characters.json');a=p.parse_args()
    update_catalog(a.root,a.revision,a.output)
