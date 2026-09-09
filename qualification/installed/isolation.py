import os, json, runpy, sys
for path in ('/work/build-core','/work/build-xacc','/work/qristal-core','/work/xacc','/work/deps','/opt/qb','/mnt/qb'):
    assert not os.path.exists(path), ('Unexpected build/source/vendor path', path)
import qristal.core as q
assert os.path.realpath(q.__file__).startswith('/work/install-core/lib/qristal/'), q.__file__
runpy.run_path('/checks/' + sys.argv[1], run_name='__main__')
if 'qristal_primitives' in sys.modules:
    assert sys.modules['qristal_primitives'].__file__.startswith('/work/install-integrations/'), sys.modules['qristal_primitives'].__file__
loaded = sorted({line.split()[-1] for line in open('/proc/self/maps') if '.so' in line and '/' in line.split()[-1]})
assert not any('/build-' in p or '/deps/' in p for p in loaded), loaded
print('ISOLATION_PASS: ' + json.dumps({'module': os.path.realpath(q.__file__), 'loaded_libraries': loaded}))
