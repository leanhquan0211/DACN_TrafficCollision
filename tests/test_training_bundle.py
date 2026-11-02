"""Kiểm projection/cloud guard để không rò test, đổi nhãn hoặc đổi recipe.

Dùng fixture nhỏ trong RAM; không Kaggle API, không GPU hoặc training thật.
"""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from src.training_bundle import full_train_projection,safe_path,verify_rows
from scripts.kaggle_b0 import notebook,execute,publish,DATASET_ID,safe_server_message,dataset_info,verify_remote_dataset,push_gpu_notebook,GPU_IMAGE,remote_logs,KERNEL_ID


def row(sequence,split,label='positive',group=None):
    return dict(source_dataset='ACCIDENT',source_sequence=sequence,source_frame='5',source_path='source.png',
        asset_kind='image',collision_label=label,label_origin='author_accident_impact_region',
        label_evidence='author.csv',accident_bbox_count='1',converted_label='source.txt',
        leakage_group=group or sequence,camera_id_verified='False',split=split,training_release_allowed='False',
        export_image='images/'+split+'/'+sequence+'.png',export_label='labels/'+split+'/'+sequence+'.txt',
        image_sha256=hashlib.sha256(sequence.encode()).hexdigest(),label_sha256=hashlib.sha256(b'box').hexdigest())


def fixture():
    base=[row('a','train'),row('b','val'),row('c','test')]
    groups=dict(model_predictions_seen_before_assignment=False,groups=[
        dict(group_id='TAD:g',sequences=['n'],assignment='train'),
        dict(group_id='TAD:v',sequences=['v'],assignment='val'),
        dict(group_id='TAD:r',sequences=['r'],assignment='reserve_negative_holdout'),
        dict(group_id='TAD:e',sequences=['e'],assignment='exclude')])
    samples=[dict(source_sequence=s,source_frame=7,image='candidate/'+s+'.png',
        collision_label='negative',label_origin='author_normal_folder_clip_label',
        image_sha256=hashlib.sha256(('candidate'+s).encode()).hexdigest()) for s in ('n','v','r','e')]
    return base,dict(samples=samples),groups


class TrainingBundleTests(unittest.TestCase):
    def test_headless_plot_smoke_survives_inherited_inline_backend(self):
        import os,subprocess,sys
        folder=Path(__file__).resolve().parents[1]/'.tmp'/('plot_fixture_'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        cell=notebook()['cells'][3]['source']
        tree=ast.parse(cell)
        smoke=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='plot_check' for t in node.targets))
        image=folder/'plot.png'
        smoke=smoke.replace('/kaggle/working/plot_backend_check.png',image.as_posix())
        command="import os; os.environ['MPLBACKEND']='Agg'; "+smoke
        env=dict(os.environ,MPLBACKEND='module://matplotlib_inline.backend_inline',MPLCONFIGDIR=str(folder/'mpl'))
        result=subprocess.run([sys.executable,'-c',command],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(image.read_bytes().startswith(b'\x89PNG'))

    def test_live_logs_select_version_and_disconnect_without_cancelling_cloud(self):
        from unittest.mock import MagicMock
        api=MagicMock();api.kernels_logs_cli.side_effect=KeyboardInterrupt
        with patch('scripts.kaggle_b0.api_client',return_value=api):
            remote_logs(follow=True,version=8)
        api.kernels_logs_cli.assert_called_once_with(KERNEL_ID+'/8',kernel_opt=None,follow=True)
        api.kernels_push.assert_not_called()
        api.kernels_cancel.assert_not_called()
        api.kernels_logs.assert_not_called()

    def test_gpu_request_serialization_and_quick_save_does_not_run(self):
        import sys
        # SDK nằm ở CLI env riêng; phép kiểm này không authenticate hoặc gọi mạng.
        sdk=Path(__file__).resolve().parents[1]/'.tmp/kaggle_cli_env/Lib/site-packages'
        with patch.object(sys,'path',[str(sdk),*sys.path]):
            try:
                from kagglesdk.kernels.types.kernels_enums import KernelExecutionType
            except ImportError:self.skipTest('Optional isolated Kaggle SDK not installed')
            from unittest.mock import MagicMock
            folder=Path(__file__).resolve().parents[1]/'.tmp'/('gpu_request_'+uuid.uuid4().hex)
            folder.mkdir(parents=True)
            (folder/'kernel-metadata.json').write_text(json.dumps(dict(id='laqun0211/dacn-b0-s960-full-v1',title='DACN B0 S960 Full V1',
                is_private=True,enable_gpu=True,dataset_sources=[DATASET_ID],code_file='test.ipynb')))
            (folder/'test.ipynb').write_text(json.dumps({'cells':[]}))
            api=MagicMock()
            for no_run in (False,True):
                push_gpu_notebook(api,folder,no_run=no_run)
                request=api.build_kaggle_client.return_value.__enter__.return_value.kernels.kernels_api_client.save_kernel.call_args.args[0]
                value=json.loads(request.to_json())
                self.assertIs(value['enableGpu'],True)
                self.assertIs(value['isPrivate'],True)
                self.assertEqual(value['machineShape'],'NvidiaTeslaT4')
                if no_run:
                    self.assertFalse(value.get('dockerImage'))
                    self.assertEqual(value['dockerImagePinningType'],'latest')
                else:self.assertEqual(value['dockerImage'],GPU_IMAGE)
                self.assertEqual(request.kernel_execution_type,KernelExecutionType.QUICK_SAVE if no_run else KernelExecutionType.SAVE_AND_RUN_ALL)

    def test_notebook_bootstrap_handles_auto_extracted_input_and_zip(self):
        import zipfile
        from unittest.mock import MagicMock
        for mode in ('extracted','zip','corrupt','no_gpu','no_internet'):
            folder=Path(__file__).resolve().parents[1]/'.tmp'/('notebook_fixture_'+uuid.uuid4().hex)
            staging=folder/'staging';(staging/'dataset').mkdir(parents=True)
            inputs=folder/'input';inputs.mkdir();working=folder/'working';working.mkdir()
            project=folder/'project'
            payload=b'locked fixture'
            manifest={'samples':1,'files':{'example.txt':{'size_bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}}}
            manifest_bytes=json.dumps(manifest).encode()
            archive=staging/'dataset/b0_full_bundle.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('example.txt',payload);z.writestr('data/training_bundle_manifest.json',manifest_bytes)
            with patch('scripts.kaggle_b0.STAGING',staging):code=notebook()['cells'][1]['source']
            if mode=='zip':
                import shutil
                shutil.copyfile(archive,inputs/archive.name)
                (inputs/'bundle_receipt.json').write_text(json.dumps({'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
            else:
                source=inputs/'b0_full_bundle';(source/'data').mkdir(parents=True)
                (source/'data/training_bundle_manifest.json').write_bytes(manifest_bytes)
                (source/'example.txt').write_bytes(b'bad' if mode=='corrupt' else payload)
            paths={'/kaggle/working':working,'/kaggle/input':inputs,'/tmp/DACN_TrafficCollision':project,'/tmp':folder}
            code=code.replace('from pathlib import Path, PurePosixPath','from pathlib import PurePosixPath')
            def mapped_path(name):
                if str(name).startswith('/kaggle/working/'):
                    return working/str(name).removeprefix('/kaggle/working/')
                return paths.get(str(name),Path(name))
            namespace={'Path':mapped_path}
            with patch('urllib.request.urlopen',side_effect=OSError('DNS unavailable') if mode=='no_internet' else None),patch('shutil.which',return_value=None if mode=='no_gpu' else '/usr/bin/nvidia-smi'),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='T4')),patch('shutil.disk_usage',return_value=SimpleNamespace(free=100*2**30)):
                if mode=='no_gpu':
                    with self.assertRaisesRegex(RuntimeError,'Phiên không có'):exec(code,namespace)
                    self.assertFalse(project.exists())
                    self.assertFalse(json.loads((working/'gpu_check.json').read_text())['training_started'])
                elif mode=='no_internet':
                    with self.assertRaisesRegex(RuntimeError,'Phiên chưa truy cập'):exec(code,namespace)
                    self.assertFalse(project.exists())
                    self.assertEqual(json.loads((working/'startup_check.json').read_text())['status'],'blocked_internet')
                elif mode=='corrupt':
                    with self.assertRaisesRegex(RuntimeError,'File khác manifest'):exec(code,namespace)
                    self.assertFalse(project.exists())
                else:
                    exec(code,namespace)
                    self.assertEqual((project/'example.txt').read_bytes(),payload)

    def test_metadata_info_wrapper_preserves_explicit_privacy(self):
        self.assertIs(dataset_info({'info':{'isPrivate':True}})['isPrivate'],True)
        self.assertIs(dataset_info({'isPrivate':False})['isPrivate'],False)
        with self.assertRaises(ValueError):dataset_info({'info':None})

    def test_remote_verification_rejects_other_bundle_and_public_dataset(self):
        from unittest.mock import MagicMock
        folder=Path(__file__).resolve().parents[1]/'.tmp'/('remote_fixture_'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        api=MagicMock()
        for private in (True,False):
            (folder/'dataset-metadata.json').write_text(json.dumps({'info':{'isPrivate':private}}))
            (folder/'bundle_receipt.json').write_text(json.dumps({'archive_sha256':'wrong'}))
            with self.assertRaises(RuntimeError):verify_remote_dataset(api,folder,{'archive_sha256':'expected'})

    def test_server_message_redacts_auth_and_signed_urls(self):
        value=safe_server_message('token=secret Bearer abc https://host/path?signature=secret')
        self.assertNotIn('secret',value)
        self.assertNotIn('abc',value)

    def test_failed_creation_keeps_reason_and_retry_does_not_upload(self):
        folder=Path(__file__).resolve().parents[1]/'.tmp'/('publish_fixture_'+uuid.uuid4().hex)
        (folder/'dataset').mkdir(parents=True);(folder/'notebook').mkdir()
        (folder/'dataset/b0_full_bundle.zip').write_bytes(b'fixture')
        (folder/'dataset/bundle_receipt.json').write_text(json.dumps(dict(archive_sha256=hashlib.sha256(b'fixture').hexdigest())))
        (folder/'notebook/kernel-metadata.json').write_text(json.dumps(dict(is_private=True,dataset_sources=[DATASET_ID])))
        from unittest.mock import MagicMock
        api=MagicMock()
        api.dataset_create_new.return_value=SimpleNamespace(status='error',error='Account verification required')
        api.dataset_metadata.side_effect=PermissionError('403')
        with patch('scripts.kaggle_b0.STAGING',folder),patch('scripts.kaggle_b0.api_client',return_value=api),patch('scripts.kaggle_b0.credentials_present',return_value=True),patch('scripts.kaggle_b0.push_gpu_notebook',side_effect=lambda *_:api.kernels_push('fixture')):
            with self.assertRaisesRegex(RuntimeError,'Account verification required'):publish()
            with self.assertRaisesRegex(RuntimeError,'No re-upload performed'):publish()
        self.assertEqual(api.dataset_create_new.call_count,1)
        api.kernels_push.assert_not_called()

    def test_only_frozen_train_candidates_extend_original_trainval(self):
        base,candidates,groups=fixture();rows,added=full_train_projection(base,candidates,groups)
        self.assertEqual(rows[:2],base[:2])
        self.assertEqual(len(added),1)
        self.assertEqual((rows[-1]['source_sequence'],rows[-1]['split']),('n','train'))
        self.assertEqual(rows[-1]['label_sha256'],hashlib.sha256(b'').hexdigest())
        self.assertNotIn('test',{r['split'] for r in rows})

    def test_unknown_or_model_derived_negative_is_not_empty_label(self):
        for changes in ({'collision_label':'unknown'},{'label_origin':'model_prediction'}):
            base,candidates,groups=fixture();candidates['samples'][0].update(changes)
            with self.assertRaises(ValueError):full_train_projection(base,candidates,groups)

    def test_old_validation_group_cannot_be_promoted_to_train(self):
        base,candidates,groups=fixture();groups['groups'][0]['group_id']='b'
        with self.assertRaises(ValueError):full_train_projection(base,candidates,groups)

    def test_assignment_must_be_frozen_before_prediction(self):
        base,candidates,groups=fixture();groups['model_predictions_seen_before_assignment']=True
        with self.assertRaises(ValueError):full_train_projection(base,candidates,groups)

    def test_identical_pixels_cannot_cross_splits(self):
        base,_,_=fixture();base[1]['image_sha256']=base[0]['image_sha256']
        with self.assertRaises(ValueError):verify_rows(base[:2])

    def test_zip_paths_cannot_escape_on_either_platform(self):
        for name in ('../secret','/absolute','C:/secret','data/../../secret','data\\secret'):
            with self.assertRaises(ValueError):safe_path(Path.cwd(),name)

    def test_notebook_cells_are_syntax_valid_and_have_no_saved_outputs(self):
        nb=notebook()
        for cell in nb['cells']:
            if cell['cell_type']=='code':
                ast.parse(cell['source']);self.assertEqual(cell['outputs'],[])
        text='\n'.join(c['source'] for c in nb['cells'])
        self.assertIn('/kaggle/working',text)
        self.assertIn('bootstrap',text)
        self.assertNotIn('KAGGLE_API_TOKEN=',text)

    def test_cloud_command_cannot_start_local_training(self):
        with patch('scripts.kaggle_b0.require_kaggle',side_effect=RuntimeError('not Kaggle')):
            with patch('subprocess.Popen') as launch:
                with self.assertRaises(RuntimeError):execute()
                launch.assert_not_called()

    def test_status_failure_after_submit_cannot_launch_second_run(self):
        # Tránh lỗi mạng sau push khiến retry đốt thêm quota của người dùng.
        folder=Path(__file__).resolve().parents[1]/'.tmp'/('publish_fixture_'+uuid.uuid4().hex)
        (folder/'dataset').mkdir(parents=True);(folder/'notebook').mkdir()
        archive=folder/'dataset/b0_full_bundle.zip';archive.write_bytes(b'fixture')
        (folder/'dataset/bundle_receipt.json').write_text(json.dumps(dict(archive_sha256=hashlib.sha256(b'fixture').hexdigest())))
        (folder/'notebook/kernel-metadata.json').write_text(json.dumps(dict(is_private=True,dataset_sources=[DATASET_ID])))
        def metadata_file(dataset,path):
            p=Path(path);p.mkdir(parents=True,exist_ok=True)
            (p/'dataset-metadata.json').write_text(json.dumps(dict(info=dict(isPrivate=True))))
        def receipt_file(dataset,name,path,force,quiet):
            (Path(path)/name).write_text(json.dumps(dict(archive_sha256=hashlib.sha256(b'fixture').hexdigest())))
        def notebook_file(kernel,path,metadata):
            p=Path(path);p.mkdir(parents=True,exist_ok=True)
            (p/'kernel-metadata.json').write_text(json.dumps(dict(is_private=True)))
        from unittest.mock import MagicMock
        api=MagicMock()
        api.dataset_create_new.return_value=SimpleNamespace(status='ok',error=None)
        temporary=RuntimeError('Read not available immediately after creation')
        temporary.response=SimpleNamespace(status_code=403)
        api.dataset_status.side_effect=[temporary,'ready'];api.dataset_metadata.side_effect=metadata_file
        api.dataset_download_file.side_effect=receipt_file
        api.kernels_push.return_value=SimpleNamespace(error=None,invalidDatasetSources=[])
        api.kernels_pull.side_effect=notebook_file;api.kernels_status.side_effect=TimeoutError('offline')
        with patch('scripts.kaggle_b0.STAGING',folder),patch('scripts.kaggle_b0.api_client',return_value=api),patch('scripts.kaggle_b0.credentials_present',return_value=True),patch('scripts.kaggle_b0.push_gpu_notebook',side_effect=lambda *_:api.kernels_push('fixture')):
            publish()
            self.assertEqual(json.loads((folder/'deployment.json').read_text())['phase'],'dataset_access_pending')
            api.kernels_push.assert_not_called()
            with self.assertRaises(RuntimeError):publish()
            self.assertTrue(json.loads((folder/'deployment.json').read_text())['kernel_submitted'])
            publish()
        self.assertEqual(api.kernels_push.call_count,1)
        self.assertEqual(api.dataset_create_new.call_count,1)
        self.assertIs(api.dataset_create_new.call_args.kwargs['public'],False)


if __name__=='__main__':unittest.main()
