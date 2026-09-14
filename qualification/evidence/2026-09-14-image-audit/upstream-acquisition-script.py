import base64,hashlib,json,pathlib,urllib.request,zipfile
out=pathlib.Path('/private/tmp/qpp-upstream-notice-candidates-20260914');out.mkdir(mode=0o700)
sha=lambda b:hashlib.sha256(b).hexdigest();receipts=[]
def fetch(url,relative):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Marqov-notice-reconciliation'}),timeout=20) as response:
  raw=response.read(65537);final=response.url
 if len(raw)>65536:raise ValueError('metadata bound')
 p=out/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 receipts.append({'path':relative,'requested_url':url,'resolved_url':final,'bytes':len(raw),'sha256':sha(raw)})
 return json.loads(raw)
def content(repo,commit,path,prefix):
 metadata=fetch(f'https://api.github.com/repos/{repo}/contents/{path}?ref={commit}',prefix+'/'+path.replace('/','_')+'.api.json')
 raw=base64.b64decode(metadata['content'],validate=False)
 if metadata['type']!='file' or len(raw)>16384:raise ValueError('notice content bound/type')
 blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 if blob!=metadata['sha']:raise ValueError('git blob identity')
 relative=prefix+'/'+path.replace('/','_');(out/relative).write_bytes(raw)
 return {'path':relative,'upstream_path':path,'commit':commit,'git_blob_sha1':blob,'bytes':len(raw),'sha256':sha(raw),'url':metadata['html_url']}
results=[]
for repo,tag,prefix,paths in [('antlr/antlr4','4.9.2','antlr',['LICENSE.txt','runtime/Python3/setup.py']),('openqasm/openpulse-python','v1.0.1','openpulse',['LICENSE','source/openpulse/setup.cfg','source/openpulse/MANIFEST.in'])]:
 ref=fetch(f'https://api.github.com/repos/{repo}/git/ref/tags/{tag}',prefix+'/tag-ref.json');obj=ref['object']
 annotated=None
 if obj['type']=='tag':
  annotated=fetch(obj['url'],prefix+'/tag-object.json');obj=annotated['object']
 if obj['type']!='commit':raise ValueError('commit expected')
 files=[content(repo,obj['sha'],path,prefix) for path in paths]
 results.append({'repository':repo,'tag':tag,'tag_object_sha':ref['object']['sha'],'commit':obj['sha'],'files':files,
                 'assessment':'Exact public release attribution candidate; not proof that this text was included in the acquired wheel or that redistribution requirements are satisfied.'})
context=pathlib.Path('/Users/david/Marqov Artifacts/qristal/qpp-context-2026-09-14')
staging=json.loads((context/'staging.json').read_bytes());local=[]
for package in ('antlr4_python3_runtime','openpulse'):
 p=next((context/'python/wheels').glob(package+'-*.whl'));raw=p.read_bytes();entry=staging['inventory'][str(p.relative_to(context))]
 if sha(raw)!=entry['sha256'] or len(raw)!=entry['bytes']:raise ValueError('wheel identity')
 with zipfile.ZipFile(p) as archive:
  names=[n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
  if len(names)!=1:raise ValueError('metadata identity')
  info=archive.getinfo(names[0])
  if info.file_size>65536:raise ValueError('wheel metadata bound')
  metadata=archive.read(names[0]);relative=package+'-wheel-METADATA.txt';(out/relative).write_bytes(metadata)
  local.append({'wheel':p.name,'wheel_sha256':sha(raw),'metadata_member':names[0],'metadata_sha256':sha(metadata),'saved_path':relative,
   'fields':[line for line in metadata.decode().splitlines() if line.startswith(('Name:','Version:','Home-page:','Project-URL:','License:'))]})
report={'schema':'qb.upstream-notice-candidates/v1','sources':results,'http_metadata':receipts,'acquired_wheel_metadata':local,
 'coverage_complete':False,'legal_conclusion':None,'limitations':['Upstream tag/license attribution candidates do not demonstrate wheel source reproducibility or grant blanket redistribution clearance.',
 'OpenPulse wheel Home-page points to openqasm/openpulse, which GitHub redirects to openqasm/openpulse-python.',
 'The unsigned ANTLR annotated tag is recorded as upstream evidence, not cryptographic author authentication.']}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(results,indent=2))
