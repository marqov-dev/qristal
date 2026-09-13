"""Acquire the recorded source-only ANTLR dependency; never execute its build."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse


def acquire(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    endpoint='https://pypi.org/pypi/antlr4-python3-runtime/4.9.2/json'
    with urlopen(endpoint,timeout=30) as response:
        metadata=json.load(response)
    sources=[x for x in metadata['urls'] if x['packagetype']=='sdist']
    if len(sources)!=1:raise ValueError('source selection')
    item=sources[0]
    if item['filename']!='antlr4-python3-runtime-4.9.2.tar.gz' or urlparse(item['url']).hostname!='files.pythonhosted.org':
        raise ValueError('source identity')
    with urlopen(item['url'],timeout=30) as response:
        data=response.read(2*1024*1024+1)
    digest=hashlib.sha256(data).hexdigest()
    if len(data)>2*1024*1024 or len(data)!=item['size'] or digest!=item['digests']['sha256']:
        raise ValueError('source content')
    (output/item['filename']).write_bytes(data)
    receipt={'name':'antlr4-python3-runtime','version':'4.9.2','filename':item['filename'],
             'url':item['url'],'metadata_url':endpoint,'sha256':digest,'bytes':len(data),
             'built':False,'installed':False}
    (output/'source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    print(json.dumps(acquire(p.parse_args().output),indent=2))
