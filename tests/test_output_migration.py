"""Kiểm cơ chế di chuyển/khôi phục trên fixture nhỏ, không đụng output thật."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.maintenance import migrate_outputs as migration
from src.storage_paths import artifact_path, artifact_catalog, new_run_folder, output_path, require_output_path, run_folder


class OutputMigrationTests(unittest.TestCase):
    def test_event_entrypoint_writes_canonical_fixture(self):
        from scripts import evaluate_events
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = {'videos':[{'video_id':'v','camera_id':'cam','source_timing_verified':False,'source_fps':None}],
                    'events':[], 'samples':[{'video_id':'v','camera_id':'cam','frame':0,'score':0.0,'label':'negative','provenance':'fixture'}]}
            source = root/'input.json'; source.write_text(json.dumps(data),encoding='utf-8')
            policy = root/'policy.json'; policy.write_text(json.dumps({'version':'fixture','threshold':0.5,'cooldown_frames':0}),encoding='utf-8')
            with patch.object(evaluate_events,'ROOT',root), patch.object(sys,'argv',[
                'evaluate_events.py','--input',str(source),'--policy',str(policy)]):
                evaluate_events.main()
            report = output_path(root,'shared_evaluation','v002_event_replay',child='report.json')
            self.assertTrue(report.is_file())
            self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['metrics']['fp'],0)

    def test_rename_verify_and_rollback_preserve_bytes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root/'outputs/audits/b2_motion_v1'
            old.mkdir(parents=True)
            (old/'evidence.json').write_bytes(b'original immutable bytes')
            groups = {'sample': ('outputs/audits/b2_motion_v1',
                                 'outputs/baselines/03_b2_motion_rules/v001_motion_pilot')}
            registry = root/'data/registries/project_explorer.json'
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps({'schema_version': 1, 'path_aliases': [{'old': groups['sample'][0], 'new': groups['sample'][1]}]}), encoding='utf-8')
            manifest = root/'outputs/audits/storage_migration_v1/manifest.json'
            with patch.object(migration, 'ROOT', root), patch.object(migration, 'MANIFEST', manifest), patch.object(migration, 'GROUPS', groups):
                self.assertEqual(artifact_path(root, old/'evidence.json'), old/'evidence.json')
                with patch.object(sys, 'argv', ['migrate_outputs.py', '--apply', '--group', 'sample']):
                    migration.main()
                dest = root/groups['sample'][1]
                self.assertEqual(artifact_path(root, old/'evidence.json'), dest/'evidence.json')
                with patch.object(sys, 'argv', ['migrate_outputs.py', '--verify', '--group', 'sample']):
                    migration.main()
                with patch.object(sys, 'argv', ['migrate_outputs.py', '--rollback', '--group', 'sample']):
                    migration.main()
                self.assertEqual((old/'evidence.json').read_bytes(), b'original immutable bytes')
                self.assertFalse(dest.exists())

    def test_destination_collision_blocks_move(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'outputs/audits/b2_motion_v1'
            dest = root/'outputs/baselines/03_b2_motion_rules/v001_motion_pilot'
            source.mkdir(parents=True); dest.mkdir(parents=True)
            (source/'a.txt').write_text('source')
            (dest/'a.txt').write_text('different')
            item = {'source': 'outputs/audits/b2_motion_v1',
                    'destination': 'outputs/baselines/03_b2_motion_rules/v001_motion_pilot',
                    **migration.scan(root, 'outputs/audits/b2_motion_v1')}
            with self.assertRaises(FileExistsError):
                migration.preflight(root, 'sample', item)
            self.assertEqual((source/'a.txt').read_text(), 'source')

    def test_canonical_output_and_legacy_catalog_roundtrip(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root/'data/registries/project_explorer.json'
            registry.parent.mkdir(parents=True)
            b0 = root/'outputs/training/old_run'
            b0.mkdir(parents=True)
            (b0/'experiment.json').write_text('{}')
            registry.write_text(json.dumps({'schema_version': 1,
                'storage_layout': {'baseline': 'outputs/baselines', 'shared_evaluation': 'outputs/shared_evaluations',
                                   'system_evidence': 'outputs/system_evidence', 'data_audit': 'outputs/data_audits'},
                'baseline_folders': [{'id': 'B0', 'folder': '01_b0_image_detection'}],
                'runs': [{'run_id': 'old_run', 'baseline': 'B0', 'version': 'v001_old',
                          'actual_path': 'outputs/training/old_run', 'storage_state': 'LEGACY'}],
                'legacy_collections': [{'path': 'outputs/training', 'category': 'baseline'}]}), encoding='utf-8')
            new = output_path(root, 'baseline', 'v002_new', baseline='B0', child='experiment.json')
            self.assertEqual(require_output_path(root, new, 'baseline', baseline='B0'), new)
            self.assertEqual(run_folder(root, 'old_run'), b0)
            with self.assertRaises(FileExistsError):
                new_run_folder(root, 'old_run', 'B0', 'v002_new')
            canonical_duplicate = output_path(root,'baseline','v001_old',baseline='B0')
            canonical_duplicate.mkdir(parents=True)
            copied = json.loads(registry.read_text(encoding='utf-8'))
            copied['runs'][0]['actual_path'] = canonical_duplicate.relative_to(root).as_posix()
            registry.write_text(json.dumps(copied), encoding='utf-8')
            with self.assertRaises(ValueError):
                run_folder(root, 'old_run')
            registry.write_text(json.dumps({'schema_version':1,
                'storage_layout': copied['storage_layout'], 'baseline_folders': copied['baseline_folders'],
                'runs':[dict(copied['runs'][0],actual_path='outputs/training/old_run')],
                'legacy_collections':copied['legacy_collections']}),encoding='utf-8')
            (canonical_duplicate/'artifact_identity.json').write_text(json.dumps({
                'run_id': 'old_run', 'baseline': 'B0'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                run_folder(root, 'old_run')
            (canonical_duplicate/'artifact_identity.json').unlink()
            with self.assertRaises(ValueError):
                require_output_path(root, root/'outputs/training/new_run', 'baseline', baseline='B0')
            with self.assertRaises(ValueError):
                output_path(root, 'data_audit', 'v2_no_padding')
            with self.assertRaises(ValueError):
                artifact_path(root, '../outside')
            rows = artifact_catalog(root)
            run = next(row for row in rows if row['id'] == 'old_run')
            self.assertEqual(run['storage_state'], 'LEGACY')
            self.assertEqual(run['physical_path'], 'outputs/training/old_run')


if __name__ == '__main__':
    unittest.main()
