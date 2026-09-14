import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import notice_overlay as overlay


def binding(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


class OverlayTests(unittest.TestCase):
    def payload(self, root):
        root.mkdir();data=b'the license';readme=b'incomplete attribution evidence'
        (root/'native').mkdir();(root/'native/LICENSE').write_bytes(data);(root/'README.txt').write_bytes(readme)
        files={'native/LICENSE':binding(data),'README.txt':binding(readme)}
        index={'schema':'qb.attribution-payload/v1','coverage_complete':False,'legal_conclusion':None,
               'notice_count':1,'entries':{'native/LICENSE':dict(binding(data),category='bundled-native')},'files':files}
        raw=json.dumps(index).encode();(root/'ATTRIBUTION_INDEX.json').write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_prepare_snapshots_index_readme_and_notices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);payload=root/'payload';digest=self.payload(payload)
            result=overlay.prepare(payload,root/'context',expected_index_sha256=digest)
            self.assertEqual(set(result['files']),{'native/LICENSE','README.txt','ATTRIBUTION_INDEX.json'})
            self.assertFalse(result['coverage_complete']);self.assertFalse(result['redistribution_cleared'])
            (payload/'README.txt').write_text('later mutation')
            self.assertEqual((root/'context/attribution/README.txt').read_bytes(),b'incomplete attribution evidence')
            checked=overlay.snapshot_context(root/'context',root/'verified',result['context_sha256'])
            self.assertEqual(result['files'],checked['files'])
            self.assertEqual((root/'context/Dockerfile').read_text(),overlay.DOCKERFILE)

    def test_wrong_external_pin_changed_readme_extra_and_symlink_rejected(self):
        for mutation in ('pin','readme','missing-readme','missing-index','extra','symlink'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);payload=root/'payload';digest=self.payload(payload)
                if mutation=='pin':digest='0'*64
                elif mutation=='readme':(payload/'README.txt').write_text('changed')
                elif mutation=='missing-readme':(payload/'README.txt').unlink()
                elif mutation=='missing-index':(payload/'ATTRIBUTION_INDEX.json').unlink()
                elif mutation=='extra':(payload/'extra').write_text('unexpected')
                else:
                    (payload/'README.txt').unlink();(payload/'README.txt').symlink_to('/unread-outside')
                with self.assertRaises((ValueError,FileNotFoundError)):overlay.prepare(payload,root/'context',expected_index_sha256=digest)
                self.assertFalse((root/'context').exists())

    def test_correlated_context_tamper_does_not_bypass_external_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);payload=root/'payload';digest=self.payload(payload)
            result=overlay.prepare(payload,root/'context',expected_index_sha256=digest)
            p=root/'context/context.json';r=json.loads(p.read_text());r['files']['README.txt']=binding(b'changed');p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'context identity'):
                overlay.snapshot_context(root/'context',root/'verified',result['context_sha256'])

    def config(self):
        return {'os':'linux','architecture':'amd64','config':{'User':'65532:65532','Env':['A=B'],'Entrypoint':['python'],'Cmd':['--capabilities']},
                'rootfs':{'type':'layers','diff_ids':['sha256:'+str(i)*64 for i in range(10)]}}

    def test_config_prefix_and_optional_runtime_fields(self):
        old=self.config();new=copy.deepcopy(old);new['rootfs']['diff_ids'].append('sha256:'+'a'*64)
        overlay.check_configs(old,new)
        for mutation in ('env','healthcheck','architecture','base-layer','extra-layer'):
            changed=copy.deepcopy(new)
            if mutation=='env':changed['config']['Env'].append('LD_PRELOAD=bad')
            elif mutation=='healthcheck':changed['config']['Healthcheck']={'Test':['CMD','bad']}
            elif mutation=='architecture':changed['architecture']='arm64'
            elif mutation=='base-layer':changed['rootfs']['diff_ids'][0]='sha256:'+'f'*64
            else:changed['rootfs']['diff_ids'].append('sha256:'+'c'*64)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):overlay.check_configs(old,changed)

    def layer(self,path,mutate=None):
        data=b'notice';name='opt/qristal/attribution/LICENSE'
        with tarfile.open(path,'w') as tar:
            for directory in ('opt','opt/qristal','opt/qristal/attribution'):
                m=tarfile.TarInfo(directory);m.type=tarfile.DIRTYPE;m.mode=0o755
                if mutate=='parent-mode' and directory=='opt':m.mode=0o777
                tar.addfile(m)
            m=tarfile.TarInfo(name);m.mode=0o644;m.size=len(data)
            if mutate=='content':data=b'NOTICE'
            if mutate=='mode':m.mode=0o4755
            if mutate=='owner':m.uid=65532
            if mutate=='symlink':m.type=tarfile.SYMTYPE;m.linkname='/etc/passwd';m.size=0
            if mutate!='missing':tar.addfile(m,io.BytesIO(data) if m.isreg() else None)
            if mutate=='duplicate':tar.addfile(m,io.BytesIO(data))
            if mutate in ('whiteout','outside'):
                extra=tarfile.TarInfo('opt/qristal/.wh.qpp_runtime.py' if mutate=='whiteout' else 'etc/evil');extra.mode=0o644
                tar.addfile(extra,io.BytesIO())
        return {'LICENSE':binding(b'notice')}

    def test_added_layer_exact_files_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'layer.tar';expected=self.layer(p)
            self.assertEqual(overlay.inspect_added_layer(p,expected)['files_verified'],1)
        for mutation in ('content','mode','owner','symlink','missing','duplicate','whiteout','outside','parent-mode'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'layer.tar';expected=self.layer(p,mutation)
                with self.assertRaises(ValueError):overlay.inspect_added_layer(p,expected)


if __name__=='__main__':unittest.main()
