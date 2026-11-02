"""Kiểm chính sách dừng, log và lineage recipe mới bằng fixture, không train."""
import hashlib
import io
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

from src.kaggle_recipe import DelayedEarlyStopping,EpochLogFilter,EpochStream,check_revised_inputs
from src.training_bundle import safe_path

ROOT=Path(__file__).resolve().parents[1]


class RecipeTests(unittest.TestCase):
    def test_resume_download_rejects_unknown_files_before_transfer(self):
        from scripts import kaggle_b0
        root=ROOT/'.tmp'/('resume_download_fixture_'+uuid.uuid4().hex)
        staging=root/'staging';download=staging/'download';download.mkdir(parents=True)
        (download/'unrelated.txt').write_text('preserve',encoding='utf-8')
        with patch.object(kaggle_b0,'ROOT',root),patch.object(kaggle_b0,'STAGING',staging),\
             patch.object(kaggle_b0,'api_client') as api:
            with self.assertRaisesRegex(ValueError,'Unexpected file'):
                kaggle_b0.fetch(version=11,resume_download=True)
            api.return_value.kernels_output.assert_not_called()
        self.assertTrue((download/'unrelated.txt').exists())

    def test_plateau_cannot_stop_before_epoch50(self):
        stopper=DelayedEarlyStopping(25,25)
        for epoch in range(1,50):self.assertFalse(stopper(epoch,.6))
        self.assertEqual(stopper.best_epoch,1)
        self.assertTrue(stopper.possible_stop)
        self.assertTrue(stopper(50,.6))

    def test_late_improvement_keeps_true_best_and_resets_wait(self):
        stopper=DelayedEarlyStopping(25,25)
        for epoch in range(1,55):self.assertFalse(stopper(epoch,.7 if epoch>=30 else .6))
        self.assertEqual(stopper.best_epoch,30)
        self.assertTrue(stopper(55,.7))
        with self.assertRaises(ValueError):DelayedEarlyStopping(25,20)

    def test_structured_epoch_chunking_deduplicates_and_suppresses_batches(self):
        row={'epoch':1,'total_epochs':60,'train/box_loss':1.1,'metrics/precision(B)':.75,'metrics/recall(B)':.62,
             'metrics/mAP50(B)':.7,'metrics/mAP50-95(B)':.55}
        payload='B0_EPOCH '+json.dumps(row)+'\n'
        stream=EpochStream(io.StringIO())
        stream.write('1/60 2.1G 1.1 1.0 1.2 1 960: 10% 3/336\r')
        stream.write(payload[:30]);stream.write(payload[30:]);stream.write(payload);stream.finish()
        text=stream.target.getvalue()
        self.assertEqual(text.count('Epoch 1/60'),1)
        self.assertIn('mAP50=70.00%',text)
        self.assertNotIn('3/336',text)

    def test_native_history_keeps_first_validation_not_final_best_reval(self):
        data='1/40 1G 1.0 1.0 1.0 1 960: 100% 100/100\n all 307 91 .8 .6 .7 .55\n'
        data+='2/40 1G 1.0 1.0 1.0 1 960: 10% 10/100\n all 307 91 .7 .5 .6 .4\n all 307 91 .8 .6 .7 .55\n'
        output=EpochLogFilter().feed(data,final=True)
        self.assertEqual(len(output),2)
        self.assertIn('mAP50=.6',output[1])
        self.assertNotIn('10/100','\n'.join(output))

    def test_errors_are_visible_even_when_batch_logs_suppressed(self):
        output=EpochLogFilter().feed('Traceback (most recent call last):\n  File train.py\nRuntimeError: OOM\n1/60 loss: 10% 2/671\n',final=True)
        self.assertIn('RuntimeError: OOM',output)
        self.assertFalse(any('2/671' in line for line in output))

    def test_oom_batch_reduction_is_visible_without_streaming_batches(self):
        line='CUDA out of memory with batch=8. Reducing to batch=4 and retrying (1/3).'
        data=line+'\n'+line+'\n1/60 3G loss: 10% 2/671\n all 307 91 .8 .6 .7 .55\n'
        output=EpochLogFilter().feed(data,final=True)
        self.assertEqual(output.count(line),1)
        self.assertNotIn('2/671','\n'.join(output))
        self.assertTrue(any('Epoch 1:' in x for x in output))

    def fixture(self):
        root=ROOT/'.tmp'/('revision_fixture_'+uuid.uuid4().hex);(root/'metadata').mkdir(parents=True)
        base={'dataset':'data/dataset.yaml','label_policy':'policy.json','initial_weights':'weights/initial.pt',
              'initial_weights_sha256':'old','portable_bundle_manifest':'manifest.json','evaluation_splits':['val'],'optimizer':'SGD'}
        new=dict(base,optimizer='AdamW',recipe_revision_manifest='metadata/revision.json')
        (root/'base.json').write_bytes(json.dumps(base).encode());(root/'new.json').write_bytes(json.dumps(new).encode())
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        revision={'config_path':'new.json','config_sha256':digest(root/'new.json'),'base_config':'base.json',
                  'base_config_sha256':digest(root/'base.json'),'changed_fields':['optimizer','recipe_revision_manifest'],'code_files':{}}
        (root/'metadata/revision.json').write_bytes(json.dumps(revision).encode())
        return root,base,new,revision

    def test_revision_checks_original_release_before_using_same_data(self):
        root,base,new,_=self.fixture()
        with patch('src.training_bundle.check_portable_inputs',return_value=('dataset',[])) as original:
            self.assertEqual(check_revised_inputs(new,root),('dataset',[]))
            original.assert_called_once_with(base,root)

    def test_revision_cannot_relabel_data_or_move_test_into_auto_eval(self):
        for field,value in (('dataset','another.yaml'),('evaluation_splits',['val','test']),('initial_weights','other.pt')):
            root,_,new,revision=self.fixture();new[field]=value
            (root/'new.json').write_bytes(json.dumps(new).encode())
            revision['config_sha256']=hashlib.sha256((root/'new.json').read_bytes()).hexdigest()
            revision['changed_fields'].append(field)
            (root/'metadata/revision.json').write_bytes(json.dumps(revision).encode())
            with self.assertRaisesRegex(ValueError,'cannot change'):check_revised_inputs(new,root)

    def test_prepared_overlay_is_byte_exact_and_cannot_overwrite_original(self):
        path=ROOT/'outputs/kaggle/b0_s960_adamw_kaggle_v2/notebook/train_b0.ipynb'
        if not path.exists():self.skipTest('Prepare recipe first to validate its generated notebook')
        nb=json.loads(path.read_text('utf-8'));code=nb['cells'][2]['source']
        root=ROOT/'.tmp'/('overlay_fixture_'+uuid.uuid4().hex);(root/'data').mkdir(parents=True)
        original=root/'scripts/train_b0.py';original.parent.mkdir();original.write_bytes(b'unchanged')
        (root/'data/training_bundle_manifest.json').write_bytes(json.dumps({'files':{'scripts/train_b0.py':{}}}).encode())
        exec(code,{'PROJECT':root,'safe_member':safe_path})
        revision=json.loads((root/'metadata/recipe_revision_adamw_v2.json').read_text('utf-8'))
        self.assertEqual(hashlib.sha256((root/revision['config_path']).read_bytes()).hexdigest(),revision['config_sha256'])
        for name,record in revision['code_files'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),record['sha256'])
        self.assertEqual(original.read_bytes(),b'unchanged')
        with self.assertRaisesRegex(RuntimeError,'already exists'):exec(code,{'PROJECT':root,'safe_member':safe_path})


if __name__=='__main__':unittest.main()
