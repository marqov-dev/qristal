"""Package an explicit public-artifact allowlist; never include a repository root."""
import hashlib,json,pathlib,subprocess,sys,tarfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=pathlib.Path(sys.argv[1]); OUT.mkdir()
entries={
 'install-core/lib':'install-core/lib', 'install-core/include':'install-core/include',
 'install-xacc/lib':'install-xacc/lib', 'install-xacc/include':'install-xacc/include',
 'install-xacc/plugins':'install-xacc/plugins',
 'install-xacc/bin/usResourceCompiler4':'install-xacc/bin/usResourceCompiler4',
 'xacc/quantum/plugins/circuits/qft':'xacc-qft',
 'build-core/lib/libgtest.a':'build-core/lib/libgtest.a',
 'build-core/lib/libgtest_main.a':'build-core/lib/libgtest_main.a',
 'build-core/algorithm_es':'build-core/algorithm_es',
 'deps/googletest/1aceeb1edcf0e5921c95e1fd1d7d8034132b5528/googletest/include':'gtest/include',
 'qristal-core/include':'qristal-core/include',
 'qristal-core/src/algorithms/exponential_search':'qristal-core/src/algorithms/exponential_search',
 'qristal-decoder/include':'qristal-decoder/include',
 'qristal-decoder/src/quantum_decoder.cpp':'qristal-decoder/src/quantum_decoder.cpp',
 'qristal-decoder/tests/FullDecoderInputValidation.cpp':'qristal-decoder/tests/FullDecoderInputValidation.cpp',
 'qristal/qualification/full_decoder/cloud/capture_process.py':'capture_process.py',
 'qristal/qualification/full_decoder/tiny_result_smoke.cpp':'qualification/full_decoder/tiny_result_smoke.cpp',
 'qristal/qualification/full_decoder/cloud/guest.py':'guest.py',
 'qristal/qualification/full_decoder/cloud/qft_activator.cpp':'qft_activator.cpp',
 'qristal/qualification/full_decoder/cloud/qft-manifest.json':'qft-manifest.json',
 'qristal/qualification/install-toolchain.sh':'install-toolchain.sh',
}
manifest={'revisions':{repo:subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/repo).decode().strip() for repo in ('qristal','qristal-core','qristal-decoder','xacc')},'entries':entries,'source_hashes':{}}
for name in entries:
 path=ROOT/name
 if not path.exists(): raise RuntimeError('missing:'+name)
 for item in ([path] if path.is_file() else path.rglob('*')):
  if not item.resolve().is_relative_to(ROOT):
   # Installed plugin links deliberately target the Linux /work prefix.
   # Validate their host counterparts before preserving these exact guest links.
   target=item.readlink() if item.is_symlink() else item
   if not target.is_relative_to('/work/install-core/lib'):
    raise RuntimeError('external_link:'+str(item))
   local=ROOT/target.relative_to('/work')
   if not local.resolve().is_relative_to(ROOT/'install-core/lib') or not local.is_file():
    raise RuntimeError('invalid_guest_link:'+str(item))
  if item.is_file() and (item.suffix in ('.cpp','.hpp','.py','.sh') or 'cppmicroservices_' in item.name) and not name.startswith(('install-', 'deps/')):
   manifest['source_hashes'][str(item.relative_to(ROOT))]=hashlib.sha256(item.read_bytes()).hexdigest()
(OUT/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
with tarfile.open(OUT/'cpu.tar.gz','w:gz',compresslevel=1,dereference=False) as archive:
 for source,target in entries.items(): archive.add(ROOT/source,arcname=target)
 archive.add(OUT/'manifest.json',arcname='manifest.json')
info={'sha256':hashlib.sha256((OUT/'cpu.tar.gz').read_bytes()).hexdigest(),'bytes':(OUT/'cpu.tar.gz').stat().st_size}
(OUT/'archive.json').write_text(json.dumps(info)+'\n');print(json.dumps(info))
