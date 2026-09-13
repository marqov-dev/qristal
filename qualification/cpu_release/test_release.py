import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import prepare
import record

HERE=Path(__file__).resolve().parent


class DeliveryTests(unittest.TestCase):
    def test_matrix_requires_backend_diagnostic_after_valid_program(self):
        def execute(bad=False):
            with tempfile.TemporaryDirectory() as temp:
                def run(cmd, **kwargs):
                    if cmd[1]=='rm':return subprocess.CompletedProcess(cmd,0,'','')
                    if '--capabilities' in cmd:out=json.dumps({'hosted_contract':'not_integrated'})
                    elif '/probe/decoder-smoke' in cmd:out='PASS:\n'*9
                    elif '/checks/isolation.py' in cmd:out='PASS: fixture\nISOLATION_PASS: fixture'
                    elif '--backend' in cmd and 'gpu' in cmd:
                        diagnostic='program_file' if bad or '--qasm' not in cmd else 'backend'
                        return subprocess.CompletedProcess(cmd,2,'','qristal_sample_failed:'+diagnostic+'\n')
                    elif '16385' in cmd:return subprocess.CompletedProcess(cmd,2,'','qristal_sample_failed:shots\n')
                    elif '--qasm' in cmd:
                        counts={'00':1638,'10':410,'11':1843,'01':205} if 'aer' in cmd else {'00':2048,'11':2048}
                        out=json.dumps({'counts':counts})
                    else:out='PASS: isolation'
                    return subprocess.CompletedProcess(cmd,0,out,'')
                with patch.object(subprocess,'run',side_effect=run),patch.object(sys,'argv',['matrix','--image','sha256:'+'a'*64,'--output',temp+'/result']):
                    runpy.run_path(str(HERE/'matrix.py'),run_name='__main__')
        execute()
        with self.assertRaises(AssertionError):execute(True)

    def test_context_derivation_preserves_parent_and_adds_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); workspace=root/'workspace';workspace.mkdir()
            for name in ('runtime.py','adapter.py','capabilities.json'):(workspace/name).write_text('fixture')
            mapping={name:'opt/qristal/'+name for name in ('runtime.py','adapter.py','capabilities.json')}
            context=root/'original/context'
            with patch.dict(prepare.stage.INPUTS,mapping,clear=True):
                prepare.stage.stage(workspace,prepare.stage.capture(workspace),context)
            original=prepare.stage.sha(context/'context.json')
            archive=root/'inputs.tar.gz'
            with tarfile.open(archive,'w:gz') as stream:stream.add(context,arcname='context')
            inputs={'archive_sha256':prepare.stage.sha(archive),'context_sha256':original}
            prepare.prepare(archive,root/'release','a'*40,inputs)
            prepare.stage.verify_context(root/'release/context')
            self.assertEqual(prepare.stage.sha(context/'context.json'),original)
            receipt=json.loads((root/'release/release-context.json').read_text())
            self.assertEqual(receipt['parent'],inputs)
            self.assertEqual(receipt['inventory_sha256'],prepare.stage.sha(root/'release/context/payload/opt/qristal/inventory.py'))
            with self.assertRaises(ValueError):prepare.prepare(archive,root/'bad','a'*40,dict(inputs,archive_sha256='0'*64))
            self.assertFalse((root/'bad').exists())

    def test_publication_receipt_does_not_claim_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'release-context.json').write_text(json.dumps({'source_revision':'a'*40}))
            record.record(root,'sha256:'+'b'*64,'a'*40,'12','1',{'containerimage.digest':'sha256:'+'b'*64})
            data=json.loads((root/'release.json').read_text())
            self.assertEqual(data['status'],'published_candidate_pending_acquired_checks')
            self.assertFalse(data['hosted_available'])
            with self.assertRaises(ValueError):record.record(root,'sha256:'+'b'*64,'c'*40,'12','1',{'containerimage.digest':'sha256:'+'b'*64})

    def test_registry_and_diagnostic_binding(self):
        spec=importlib.util.spec_from_file_location('cpu_release_verifier',HERE/'verify.py')
        verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'acquired').mkdir()
            def write(name,data):
                (root/name).write_text(json.dumps(data));return 'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest()
            revision='a'*40;configuration='sha256:'+'b'*64
            platform_digest=write('platform-manifest.json',{'config':{'digest':configuration}})
            digest=write('registry-index.json',{'manifests':[{'platform':{'os':'linux','architecture':'amd64'},'digest':platform_digest}]})
            context={'schema':'marqov.cpu-release-context/v1','source_revision':revision,'parent':verifier.read_inputs(),
                     'matrix_sha256':hashlib.sha256((HERE/'matrix.py').read_bytes()).hexdigest(),
                     'inventory_sha256':hashlib.sha256((HERE/'inventory.py').read_bytes()).hexdigest(),
                     'payload_hashes':{n:'c'*64 for n in ('runtime.py','adapter.py','capabilities.json')}}
            write('release-context.json',context)
            release={'schema':'marqov.cpu-release/v1','status':'published_candidate_pending_acquired_checks',
                     'hosted_available':False,'image':'ghcr.io/marqov-dev/qristal-cpu@'+digest,'source_revision':revision,
                     'context':context,'workflow_run':'https://github.com/marqov-dev/qristal/actions/runs/1/attempts/1'}
            write('release.json',release);write('build-metadata.json',{'containerimage.digest':digest})
            write('image-inspect.json',[{'Id':configuration,'Config':{'User':'65532:65532','Entrypoint':['python3','/opt/qristal/runtime.py'],
                 'Cmd':['--capabilities'],'WorkingDir':'/tmp','Labels':{'org.opencontainers.image.source':'https://github.com/marqov-dev/qristal','org.opencontainers.image.revision':revision}}}])
            tests=[]
            for name in ('capabilities','core','noise','integration','decoder','bell','noisy-bell','reject-shots','reject-gpu','isolation'):
                cmd=verifier.native.expected_command(name,'marqov-runtime-test-0123456789',configuration)
                if name=='reject-gpu':cmd=cmd[:-2]+['--qasm','/checks/bell.qasm','--backend','gpu']
                tests.append({'name':name,'command':cmd,'exit':2 if name.startswith('reject-') else 0})
            write('acquired/image-tests.json',{'image':configuration,'tests':tests,'no_host_mounts':True})
            (root/'acquired/image-reject-gpu.log').write_text('qristal_sample_failed:backend\n')
            write('inventory.json',{'uid':65532,'architecture':'x86_64','payload':dict(context['payload_hashes'],**{'inventory.py':context['inventory_sha256']}),
                                   'python_environments':{'core':['fixture'],'integrations':['fixture']},'dpkg':'fixture','notices':['fixture']})
            write('sbom.json',{});write('provenance.json',{})
            slsa={'buildDefinition':{'externalParameters':{'request':{'root':{'request':{'args':{'vcs:revision':revision,'vcs:source':'https://github.com/marqov-dev/qristal'}}}}}},
                  'runDetails':{'builder':{'id':release['workflow_run']}}}
            with patch.object(verifier.attest,'check'),patch.object(verifier.attest,'document',return_value=slsa):
                self.assertTrue(verifier.verify(root)['backend_rejection_verified'])
                (root/'acquired/image-reject-gpu.log').write_text('qristal_sample_failed:program_file\n')
                with self.assertRaises(ValueError):verifier.verify(root)
                (root/'acquired/image-reject-gpu.log').write_text('qristal_sample_failed:backend\n')
                bad=copy.deepcopy(context);bad['matrix_sha256']='0'*64
                write('release-context.json',bad)
                with self.assertRaises(ValueError):verifier.verify(root)
                write('release-context.json',context)
                write('platform-manifest.json',{'config':{'digest':'sha256:'+'d'*64}})
                with self.assertRaises(ValueError):verifier.verify(root)

    def test_retained_release_and_compressed_shadow_rejection(self):
        import shutil
        spec=importlib.util.spec_from_file_location('cpu_retention_test',HERE/'retained.py')
        retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
        source=HERE.parent/'evidence/2026-09-13-cpu-published'
        self.assertTrue(retained.verify(source)['native_passed'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'bundle';shutil.copytree(source,root)
            (root/'sbom.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'ambiguous_stored_record'):retained.verify(root)
