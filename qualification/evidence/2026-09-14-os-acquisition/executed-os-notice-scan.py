import hashlib,io,json,pathlib,posixpath,re,tarfile
ROOT=pathlib.Path('/private/tmp/qpp-os-acquisition-trusted-20260914')
sha=lambda b:hashlib.sha256(b).hexdigest()
virtual={};sources={};packages=[]
def ar_data(path):
 raw=path.read_bytes()
 if len(raw)>100*1024**2 or raw[:8]!=b'!<arch>\n':raise ValueError('ar bound/header')
 pos=8;found=None
 while pos<len(raw):
  header=raw[pos:pos+60]
  if len(header)!=60 or header[58:]!=b'`\n':raise ValueError('ar header')
  size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
  if size<0 or pos+60+size>len(raw):raise ValueError('ar size')
  if name.startswith('data.tar'):
   if found is not None:raise ValueError('duplicate data')
   found=raw[pos+60:pos+60+size]
  pos+=60+size+(size%2)
 if found is None:raise ValueError('missing data')
 return raw,found

def scan(stream,source):
 total=0;count=0
 with tarfile.open(fileobj=stream,mode='r|*') as archive:
  for member in archive:
   count+=1;total+=member.size
   if count>100000 or total>512*1024**2 or member.size<0:raise ValueError('tar bounds')
   name=member.name.removeprefix('./').rstrip('/')
   if name.startswith('/') or '..' in pathlib.PurePosixPath(name).parts:raise ValueError('tar path')
   if not(name.startswith('usr/share/doc/') or name.startswith('usr/share/common-licenses/')):continue
   item={'source':source,'archive_path':member.name,'mode':member.mode,'bytes':member.size}
   if member.issym():item.update(type='symlink',target=member.linkname)
   elif member.islnk():item.update(type='hardlink',target=member.linkname)
   elif member.isdir():item.update(type='directory')
   elif member.isfile():
    item.update(type='file')
    if pathlib.PurePosixPath(name).name=='copyright' or name.startswith('usr/share/common-licenses/'):
     if member.size>8*1024**2:raise ValueError('notice bound')
     raw=archive.extractfile(member).read(8*1024**2+1)
     if len(raw)!=member.size:raise ValueError('notice size')
     item.update(sha256=sha(raw),common_license_references=sorted(set(ref.rstrip('.') for ref in re.findall(r'/usr/share/common-licenses/([A-Za-z0-9.+_-]+)',raw.decode(errors='replace')))))
   else:raise ValueError('documentation special member')
   virtual[name]=item

base=ROOT/'base-docs.tar';raw=base.read_bytes();sources[base.name]={'bytes':len(raw),'sha256':sha(raw)}
scan(io.BytesIO(raw),base.name)
for path in sorted((ROOT/'debs').glob('*.deb')):
 raw,data=ar_data(path);sources[path.name]={'bytes':len(raw),'sha256':sha(raw)}
 scan(io.BytesIO(data),path.name);packages.append((path.name.split('_')[0],path.name))

def resolve(name):
 chain=[];seen=set()
 while True:
  if name in seen:return None,chain,'link cycle'
  seen.add(name)
  parts=name.split('/');changed=False
  for i in range(1,len(parts)+1):
   prefix='/'.join(parts[:i]);item=virtual.get(prefix)
   if item and item['type'] in ('symlink','hardlink'):
    target=item['target']
    target=target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(prefix),target) if item['type']=='symlink' else target.removeprefix('./')
    target=posixpath.normpath(posixpath.join(target,*parts[i:]))
    if not(target.startswith('usr/share/doc/') or target.startswith('usr/share/common-licenses/')):return None,chain,'target outside documentation'
    chain.append({'path':prefix,'target':item['target'],'source':item['source']});name=target;changed=True;break
  if changed:
   if len(chain)>64:return None,chain,'link bound'
   continue
  item=virtual.get(name)
  if item is None or item['type']!='file' or 'sha256' not in item:return None,chain,'notice file missing'
  return dict(item,resolved_path=name),chain,None

results=[]
for package,archive in packages:
 requested='usr/share/doc/'+package+'/copyright';file,chain,error=resolve(requested)
 common=[]
 if file:
  for ref in file['common_license_references']:
   ref_file,ref_chain,ref_error=resolve('usr/share/common-licenses/'+ref)
   common.append({'name':ref,'file':ref_file,'chain':ref_chain,'error':ref_error})
 results.append({'package':package,'deb':archive,'requested_path':requested,'file':file,'link_chain':chain,'error':error,'common_licenses':common})
report={'schema':'qb.os-notice-observations/v1','scanner_sha256':sha(pathlib.Path(__file__).read_bytes()),'inputs':sources,'selected_package_count':len(results),'resolved_count':sum(r['file'] is not None for r in results),'packages':results,'coverage_complete':False,'legal_conclusion':None,'collection_method':'Copy only each resolved regular file archive_path from its bound source archive using bounded member reads to a distinct notices/package/copyright destination. Resolve links in the virtual documentation inventory; do not dereference host paths. Also collect referenced common license regular files from bound base-docs.tar or package archives. Preserve original copyright text bytes and SHA256 receipts.','limitations':['Only 36 selected debs checked; base OS package coverage requires its package inventory.','References parsed from copyright text are hints, not a complete attribution or legal review.','No packages installed, scripts executed, or archives extracted to filesystem.']}
out=pathlib.Path('/private/tmp/qpp-os-notice-observations-20260914.json');out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'packages':len(results),'resolved':report['resolved_count'],'linked':[r['package'] for r in results if r['link_chain']],'missing':[r['package'] for r in results if r['error']],'missing_common':[{'package':r['package'],'name':c['name'],'error':c['error']} for r in results for c in r['common_licenses'] if c['error']]},indent=2))
