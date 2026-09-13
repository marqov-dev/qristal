import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('core_result',Path(__file__).with_name('check_result.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class Tests(unittest.TestCase):
    def fixture(self,root,mutate_log=None):
        protocol=root/'protocol.json';protocol.write_text(json.dumps({'materials_sha256':'a'*64}))
        image='sha256:'+'b'*64
        report={'kind':'qb-core-native/v1','native_passed':True,'materials_sha256':'a'*64,
                'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
                'builder_image':image,'stages':{},'plugin_normalization':{'schema':'qb.core-plugin-normalization/v1','changes':[]}}
        logs={n:'ok\n' for n in c.STAGES}
        logs.update({'install-audit':json.dumps({'passed':True}),'normalize-links':json.dumps(report['plugin_normalization']),'verify-inputs':json.dumps({'verified':True,'manifest_sha256':'a'*64}),
            'xacc-replay':'PASS: ACZ registered',
            'consumer-cpp':'PASS: installed Core C++ QPP identity and Bell',
            'consumer-python':'PASS: installed Core Python QPP identity and Bell',
            'installed-linkage':'libcore.so => /work/install-core/lib/libcore.so (0x01)'})
        for name in ('source-audit','source-audit-built'):logs[name]=json.dumps({'only_generated_header_changed':True})
        for name in ('selection','selection-built'):logs[name]=json.dumps({'actual_cpm_sources_verified':True,'input_audit':{'passed':True}})
        if mutate_log:mutate_log(logs)
        archive=root/'output.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for index,name in enumerate(c.STAGES):
                data=logs[name].encode();entry=tarfile.TarInfo('logs/'+name+'.log');entry.size=len(data)
                tar.addfile(entry,io.BytesIO(data))
                report['stages'][name]={'index':index,'exit':0,'timeout':False,'container_removed':True,
                    'command':c.command(name,image),'log_sha256':hashlib.sha256(data).hexdigest()}
        return report,protocol,archive
    def test_complete_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));self.assertTrue(c.classify(*args)['native_passed'])
        self.assertFalse(c.classify({'native_passed':False},'/nonexistent','/nonexistent')['native_passed'])
    def test_missing_stage_identity_and_order(self):
        for mutation in (lambda r:r['stages'].pop('normalize-links'),
                         lambda r:r.update(materials_sha256='c'*64),
                         lambda r:r['stages']['normalize-links'].update(index=18),
                         lambda r:r['stages']['build'].update(exit=True),
                         lambda r:r['stages']['build'].update(timeout=True)):
            with tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp));mutation(args[0]);self.assertFalse(c.classify(*args)['native_passed'])
    def test_container_confinement_and_mounts(self):
        for mutation in (lambda cmd:cmd.append('--privileged'),
                         lambda cmd:cmd.__setitem__(cmd.index('none'),'host'),
                         lambda cmd:cmd.__setitem__(cmd.index('65532:65532'),'0:0'),
                         lambda cmd:cmd.insert(2,'--mount=type=bind,source=/work/inputs,target=/inputs')):
            with tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp));mutation(args[0]['stages']['consumer-python']['command'])
                self.assertFalse(c.classify(*args)['native_passed'])
    def test_archived_failure_cannot_hide_in_tail(self):
        for name,data in [('installed-linkage','not found\n'+'ok\n'*2000),
                          ('selection-built',json.dumps({'actual_cpm_sources_verified':True,'input_audit':{'passed':False}})),
                          ('source-audit','{}'),('consumer-python','no fixture marker')]:
            with tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp),lambda logs:logs.update({name:data}))
                self.assertFalse(c.classify(*args)['native_passed'])
    def test_log_hash_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));args[0]['stages']['consumer-cpp']['log_sha256']='0'*64
            self.assertFalse(c.classify(*args)['native_passed'])
