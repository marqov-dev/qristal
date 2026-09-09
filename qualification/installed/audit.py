import pathlib, subprocess, json
roots=[pathlib.Path('/work/install-core'),pathlib.Path('/work/install-xacc')]
assert not pathlib.Path('/work/build-core').exists()
report=[]
for root in roots:
 for path in sorted(root.rglob('*')):
  if path.is_symlink():
   assert path.exists(), ('Broken install link',str(path),str(path.readlink()))
   resolved=str(path.resolve())
   assert resolved.startswith(tuple(str(r)+'/' for r in roots)), ('External install link',str(path),resolved)
  if path.is_symlink() or not path.is_file() or '.so' not in path.name:continue
  with path.open('rb') as f:
   if f.read(4)!=b'\x7fELF':continue
  p=subprocess.run(['ldd',str(path)],capture_output=True,text=True)
  assert p.returncode==0 and 'not found' not in p.stdout, (str(path),p.stdout,p.stderr)
  dynamic=subprocess.run(['readelf','-d',str(path)],capture_output=True,text=True,check=True).stdout
  search=[line.strip() for line in dynamic.splitlines() if 'RPATH' in line or 'RUNPATH' in line]
  report.append({'library':str(path),'search_paths':search,'linkage':p.stdout.splitlines()})
print('PASS: '+json.dumps({'shared_libraries':report},indent=2))
