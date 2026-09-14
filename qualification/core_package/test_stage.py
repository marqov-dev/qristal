import importlib.util
import io
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('core_stage',HERE/'stage.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
fixtures=stage.AUDIT.load('stage_output_fixtures',HERE.parent/'core_output/test_output.py')


class StageTests(unittest.TestCase):
    def fixture(self,root):
        source=root/'source';source.mkdir()
        report,roots=fixtures.OutputTests().fixture(source,True)
        (source/'install-core/lib/libcircuits.so.1.8.1').chmod(0o755)
        archive=source/'output.tar.gz';identity=stage.AUDIT.OUTPUT.pack(archive,report,roots)
        with tarfile.open(archive) as stream:inventory=json.load(stream.extractfile('receipt.json'))['entries']
        receipts=[]
        for name in ('protocol.json','native.json','materials.json'):
            path=source/name;path.write_text('{}');receipts.append(path)
        wheels=source/'wheels';wheels.mkdir();required=[]
        for n in range(50):
            path=wheels/('synthetic-'+str(n)+'.whl');path.write_bytes(('wheel'+str(n)).encode())
            required.append({'filename':path.name,'bytes':path.stat().st_size,'sha256':stage.AUDIT.sha(path)})
        plan={'required_python':{'wheels':required,'antlr':dict(inventory['antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl'],archive_path='antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl')},'retained_inventory':inventory,'scope':'synthetic QPP-only',
              'bindings':{'archive_sha256':identity['sha256']},'evidence_provenance':{'mode':'synthetic fixture'}}
        def audit(snapshot,*args):
            self.assertNotEqual(snapshot,archive)
            stage.AUDIT.OUTPUT.verify(snapshot,identity,report)
            return plan
        return (archive,*receipts,wheels,root/'context'),audit,plan

    def test_stage_preserves_layout_links_modes_and_exact_wheels(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,_=self.fixture(Path(tmp))
            with patch.object(stage.AUDIT,'audit',side_effect=audit):result=stage.stage(*args)
            context=args[-1]
            self.assertFalse((context/'work').exists())
            with tarfile.open(context/'work.tar') as payload:
                library=payload.getmember('install-core/lib/libcircuits.so.1.8.1')
                link=payload.getmember('install-xacc/plugins/libcircuits.so.1.8.1')
                self.assertEqual(link.linkname,'../../install-core/lib/libcircuits.so.1.8.1')
                self.assertEqual(payload.extractfile(library).read(),b'library')
                self.assertEqual(library.mode,0o755)
            self.assertEqual(result['inventory']['work.tar']['sha256'],stage.AUDIT.sha(context/'work.tar'))
            self.assertEqual(len(list((context/'python/wheels').iterdir())),51)
            self.assertFalse(result['runtime_qualified'])
            self.assertIn('runtime/qpp_runtime.py',result['inventory'])
            self.assertEqual(result['inventory']['evidence/recipe.py']['sha256'],result['recipe_sha256'])
            self.assertEqual(result['inventory']['runtime-recipe.json']['sha256'],stage.AUDIT.sha(context/'runtime-recipe.json'))
            self.assertFalse(json.loads((context/'runtime-recipe.json').read_text())['build_ready'])
            self.assertFalse((context/'evidence/archive.tar.gz').exists())
            self.assertFalse(list(Path(tmp).glob('.core-stage-*')))

    def test_case_distinct_headers_survive_without_host_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);context=root/'context';(context/'python/wheels').mkdir(parents=True)
            archive=root/'source.tar.gz';inventory={}
            with tarfile.open(archive,'w:gz') as payload:
                for name in ('install-core','install-xacc','install-xacc/include'):
                    member=tarfile.TarInfo(name);member.type=tarfile.DIRTYPE;member.mode=0o755
                    payload.addfile(member);inventory[name]={'type':'directory','mode':0o755}
                for name,raw in [('install-xacc/include/JSON.hpp',b'upper'),('install-xacc/include/json.hpp',b'lower'),
                                 ('antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl',b'wheel')]:
                    member=tarfile.TarInfo(name);member.size=len(raw);member.mode=0o644
                    payload.addfile(member,io.BytesIO(raw))
                    inventory[name]={'type':'file','mode':0o644,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            selected=stage.retain_installs(archive,context,inventory)
            with tarfile.open(context/'work.tar') as payload:
                self.assertEqual(payload.extractfile('install-xacc/include/JSON.hpp').read(),b'upper')
                self.assertEqual(payload.extractfile('install-xacc/include/json.hpp').read(),b'lower')
            self.assertIn('install-xacc/include/JSON.hpp',selected)
            self.assertIn('install-xacc/include/json.hpp',selected)
            self.assertFalse((context/'work').exists())

    def test_changed_wheel_rejected_without_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,_=self.fixture(Path(tmp))
            next(args[-2].iterdir()).write_bytes(b'changed')
            with patch.object(stage.AUDIT,'audit',side_effect=audit),self.assertRaises(ValueError):stage.stage(*args)
            self.assertFalse(args[-1].exists())

    def test_missing_extra_or_symlink_wheels_rejected(self):
        for variation in ('missing','extra','symlink'):
            with self.subTest(variation=variation),tempfile.TemporaryDirectory() as tmp:
                args,audit,_=self.fixture(Path(tmp));wheel=next(args[-2].iterdir())
                if variation=='missing':wheel.unlink()
                elif variation=='extra':(args[-2]/'extra.whl').write_bytes(b'extra')
                else:
                    copy=Path(tmp)/'outside.whl';copy.write_bytes(wheel.read_bytes());wheel.unlink();wheel.symlink_to(copy)
                with patch.object(stage.AUDIT,'audit',side_effect=audit),self.assertRaises((ValueError,OSError)):stage.stage(*args)
                self.assertFalse(args[-1].exists())

    def test_snapshot_protects_against_later_original_archive_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,_=self.fixture(Path(tmp))
            def mutate(*a):
                result=audit(*a);args[0].write_bytes(b'replaced original');return result
            with patch.object(stage.AUDIT,'audit',side_effect=mutate):stage.stage(*args)
            self.assertTrue((args[-1]/'work.tar').is_file())

    def test_invalid_native_receipt_real_audit_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,_,_=self.fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError,'successful native evidence'):stage.stage(*args)
            self.assertFalse(args[-1].exists())

    def test_archive_verifier_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,_=self.fixture(Path(tmp));args[0].write_bytes(b'not archive')
            with patch.object(stage.AUDIT,'audit',side_effect=audit),self.assertRaises(ValueError):stage.stage(*args)
            self.assertFalse(args[-1].exists())

    def test_preexisting_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,_=self.fixture(Path(tmp));args[-1].mkdir();sentinel=args[-1]/'keep';sentinel.write_text('keep')
            with patch.object(stage.AUDIT,'audit',side_effect=audit) as mocked,self.assertRaises(FileExistsError):stage.stage(*args)
            mocked.assert_not_called();self.assertEqual(sentinel.read_text(),'keep')

    def test_subset_links_cannot_target_omitted_proof_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,plan=self.fixture(Path(tmp))
            plan['retained_inventory']['install-core/escape']={'type':'symlink','mode':0o777,'target':'../consumer/core.cpp'}
            with patch.object(stage.AUDIT,'audit',side_effect=audit),self.assertRaisesRegex(ValueError,'dangling link'):stage.stage(*args)
            self.assertFalse(args[-1].exists())

    def test_receipt_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,audit,_=self.fixture(Path(tmp));args[1].unlink();args[1].symlink_to(args[2])
            with patch.object(stage.AUDIT,'audit',side_effect=audit),self.assertRaises(OSError):stage.stage(*args)
            self.assertFalse(args[-1].exists())

if __name__=='__main__':unittest.main()
