import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_image_probe as probe

IMAGE='sha256:'+'a'*64


class NativeTests(unittest.TestCase):
    def capture(self,command,**kwargs):
        self.commands.append(command)
        if command[0]=='uname':return 0,b'Linux x86_64\n',b''
        if command[:3]==['docker','context','inspect']:return 0,b'local\n',b''
        if command[:2]==['docker','info']:return 0,json.dumps({'architecture':self.daemon_arch,'os':'linux'}).encode(),b''
        if command[:3]==['docker','image','inspect']:return 0,json.dumps({'id':IMAGE,'architecture':'amd64','os':'linux'}).encode(),b''
        if command[:3]==['docker','rm','-f']:return 0,b'',b''
        if command[:3]==['docker','container','inspect']:
            if self.bad_cleanup:return 0,b'existing-id\n',b''
            return 1,b'\n',('Error response from daemon: No such container: '+command[-1]+'\n').encode()
        self.assertEqual(command[:2],['docker','run'])
        if '--entrypoint' in command:
            if '-c' in command:
                data={'schema':'qb.qpp-five-imports/v1','passed':True,'imports':[{'module':name,'file':'/work/'+name,'version':None} for name in probe.MODULES]}
                marker='QPP_IMPORT_AUDIT '
            else:
                mode=command[-1];roots=['numpy'] if mode=='numpy' else ['numpy','scipy']
                libs=[{'path':'/work/python-core/lib/python3.10/site-packages/'+root+'.libs/'+name+'.so','bytes':1,'sha256':'b'*64}
                      for root in roots for name in ('libopenblas','libgfortran','libquadmath')]
                data={'schema':'qb.qpp-installed-wheel-linkage/v1','passed':True,'mode':mode,'loader_overrides':False,
                      'svd_reconstruction_passed':True,'matrix_product':[[10.,5.],[5.,5.]],'solution':[2.,3.],'mapped_libraries':libs}
                marker='QPP_WHEEL_AUDIT '
                if self.bad_wheel:data['mapped_libraries']=[]
            if self.command_failure:return 2,b'',b'audit failed\n'
            return 0,(marker+json.dumps(data)+'\n').encode(),b''
        args=command[command.index(IMAGE)+1:]
        if '--backend' in args:return 2,b'',b'qristal_sample_failed:backend\n'
        if '--readout-p10' in args:return 2,b'',b'qristal_sample_failed:noise_backend\n'
        if '--capabilities' in args:return 0,b'{"backends":["qpp"],"noise_cli":[]}\n',b''
        label=Path(args[args.index('--qasm')+1]).stem
        mount=command[command.index('--mount')+1]
        folder=mount.split('source=',1)[1].split(',target=',1)[0]
        digest=hashlib.sha256((Path(folder)/(label+'.qasm')).read_bytes()).hexdigest()
        data={'backend':'qpp','shots':256,'bit_order':'qubit_0_first','program_sha256':digest,
              'counts':{'00':128,'11':128} if label=='bell' else {'10':256} if label=='q0' else {'00':256}}
        return 0,json.dumps(data).encode(),b''

    def setUp(self):
        self.commands=[];self.daemon_arch='x86_64';self.bad_cleanup=False;self.bad_wheel=False;self.command_failure=False

    def run_probe(self,root,*,system='Linux',machine='x86_64',env=None):
        with patch.object(probe.platform,'system',return_value=system),patch.object(probe.platform,'machine',return_value=machine), \
             patch.dict(os.environ,env or {},clear=True),patch.object(probe.bounded,'capture',side_effect=self.capture):
            return probe.run(IMAGE,Path(root)/'result.json')

    def test_all_cases_preserve_raw_local_receipt_and_native_scope(self):
        with tempfile.TemporaryDirectory() as root:
            result=self.run_probe(root)
            self.assertTrue(result['passed']);self.assertTrue(result['native_host_observed'])
            for key in ('hardware_certified','hosted','redistribution_cleared'):self.assertIs(result[key],False)
            raw=(Path(root)/'result.local-probe.json').read_bytes()
            self.assertEqual(json.loads(raw),result['local_probe'])
            self.assertFalse(result['local_probe']['native_amd64_hardware'])
            self.assertEqual(result['local_receipt']['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual([c['case'] for c in result['cases']],['imports','numpy','scipy'])
            self.assertTrue(all(c['cleanup']['absence_verified'] for c in result['cases']))
            runs=[c for c in self.commands if c[:2]==['docker','run']];self.assertEqual(len(runs),9)
            for c in runs:
                self.assertEqual(c[c.index('--network')+1],'none');self.assertIn('--read-only',c)
                self.assertEqual(c[c.index('--user')+1],'65532:65532')

    def test_wrong_host_or_remote_environment_never_calls_docker(self):
        cases=[dict(machine='aarch64'),dict(system='Darwin'),dict(env={'DOCKER_HOST':'ssh://secret@remote'}),dict(env={'DOCKER_CONTEXT':'remote'})]
        for opts in cases:
            self.commands=[]
            with self.subTest(opts=opts),tempfile.TemporaryDirectory() as root:
                result=self.run_probe(root,**opts);self.assertFalse(result['passed']);self.assertFalse(result['native_host_observed'])
                self.assertEqual(self.commands,[]);self.assertNotIn('secret',json.dumps(result))

    def test_wrong_daemon_architecture_fails_before_runtime(self):
        self.daemon_arch='aarch64'
        with tempfile.TemporaryDirectory() as root:
            result=self.run_probe(root);self.assertFalse(result['passed']);self.assertFalse(result['native_host_observed'])
            self.assertEqual(len(result['host_commands']),3)
            self.assertFalse(any(c[:2]==['docker','run'] for c in self.commands))

    def test_malformed_wheel_result_and_failed_commands_fail(self):
        for field in ('bad_wheel','command_failure'):
            setattr(self,field,True)
            with self.subTest(field=field),tempfile.TemporaryDirectory() as root:
                result=self.run_probe(root);self.assertFalse(result['passed'])
                self.assertTrue(all(c['cleanup']['absence_verified'] for c in result['cases']))
            setattr(self,field,False)

    def test_cleanup_failure_prevents_success(self):
        self.bad_cleanup=True
        with tempfile.TemporaryDirectory() as root:
            result=self.run_probe(root);self.assertFalse(result['passed'])
            self.assertFalse(result['local_probe']['passed'])

    def test_added_probe_cleanup_failure_and_inspect_after_remove_error(self):
        self.bad_cleanup=True
        with patch.object(probe.bounded,'capture',side_effect=self.capture):
            result=probe.case('imports',IMAGE,Path('/unused'))
        self.assertFalse(result['passed']);self.assertFalse(result['cleanup']['absence_verified'])
        self.bad_cleanup=False
        def capture(command,**kwargs):
            if command[:3]==['docker','rm','-f']:raise RuntimeError('simulated timeout')
            return self.capture(command,**kwargs)
        with patch.object(probe.bounded,'capture',side_effect=capture):
            result=probe.case('imports',IMAGE,Path('/unused'))
        self.assertTrue(result['cleanup']['absence_verified'])
        self.assertEqual(result['cleanup']['remove_error'],'RuntimeError')

    def test_malformed_imports_duplicate_json_and_unsafe_mapping(self):
        for text in ('QPP_IMPORT_AUDIT {}\n','QPP_IMPORT_AUDIT {"passed":true,"passed":true}\n','not json'):
            with self.assertRaises(ValueError):probe.audit_valid('imports',text)

    def test_invalid_image_refuses_execution(self):
        with tempfile.TemporaryDirectory() as root,patch.object(probe.bounded,'capture') as capture:
            with self.assertRaises(ValueError):probe.run('mutable:tag',Path(root)/'result.json')
            capture.assert_not_called()


if __name__=='__main__':unittest.main()
