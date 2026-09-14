"""Exercise wheel BLAS/LAPACK through installed loaders, without library-path overrides."""
import hashlib
import json
import os
from pathlib import Path
import sys


def mappings_cover(mode, paths):
    roots=('numpy', 'scipy') if mode=='scipy' else ('numpy',)
    return all(all(any('/'+root+'.libs/' in name and token in Path(name).name
                       for name in paths) for token in ('openblas','libgfortran','libquadmath'))
               for root in roots)


def main(mode):
    if mode not in ('numpy','scipy'):raise ValueError('fixed module mode')
    if os.environ.get('LD_LIBRARY_PATH') or os.environ.get('LD_PRELOAD'):
        raise ValueError('loader override not allowed')
    import numpy as np
    a=np.array([[3.,1.],[1.,2.]])
    assert np.allclose(a@a,[[10.,5.],[5.,5.]])
    if mode=='scipy':
        import scipy.linalg as la
    else:la=np.linalg
    solution=la.solve(a,[9.,8.]);assert np.allclose(solution,[2.,3.])
    u,s,v=la.svd(a);assert np.allclose((u*s)@v,a)
    paths=set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)==6 and ('/numpy.libs/' in fields[5] or '/scipy.libs/' in fields[5]):paths.add(fields[5])
    libs=[]
    for name in sorted(paths):
        path=Path(name);h=hashlib.sha256()
        with path.open('rb') as stream:
            while chunk:=stream.read(1024*1024):h.update(chunk)
        libs.append({'path':name,'sha256':h.hexdigest(),'bytes':path.stat().st_size})
    assert mappings_cover(mode,[item['path'] for item in libs])
    print('QPP_WHEEL_AUDIT '+json.dumps({'schema':'qb.qpp-installed-wheel-linkage/v1','mode':mode,
          'passed':True,'matrix_product':(a@a).tolist(),'solution':solution.tolist(),'svd_reconstruction_passed':True,
          'mapped_libraries':libs,'loader_overrides':False,'standalone_ldd_is_not_import_context':True},sort_keys=True))

if __name__=='__main__':main(sys.argv[1])
