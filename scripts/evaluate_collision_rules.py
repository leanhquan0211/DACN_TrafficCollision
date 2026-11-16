"""Replay verified tracks and measure development errors; never passes GT to rules."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_inference_outputs import inspect_report
from scripts.run_b0_feasibility import iou
from src.collision_rules import CollisionRules
from src.data_preparation import save_json, sha256_file


DEFAULT_REPORTS = [
    'outputs/demo_2026-11-14/cadp_001407_clean_display20fps/cadp_001407_clean_display20fps_tracking.run.json',
    *[f'outputs/inference_2026-11-14/MVI_{s}/MVI_{s}_tracking.run.json' for s in ('20011','20012','20032')],
    'outputs/demo_app/runs/6113376e6e85471f9a16fe0daf0d6a74/video/video_tracking.run.json',
]


def evaluate(paths, config, output):
    output.mkdir(parents=True, exist_ok=False)
    save_json(output/'config.json',config)
    shutil.copyfile(ROOT/'src/collision_rules.py',output/'collision_rules.py')
    truth = {}
    for r in csv.DictReader((ROOT/'data/processed/b0_proposals/001407/objects_normalized.csv').open()):
        if r['gt_id'] in ('0','2'):
            truth[int(r['source_frame']),int(r['gt_id'])] = [float(r[k]) for k in ('xmin','ymin','xmax','ymax')]
    summaries = []
    for number, path in enumerate(paths):
        inspect_report(path)
        report = json.loads(path.read_text())
        if report['mode'] != 'tracking':
            raise ValueError('Collision replay requires actual tracks')
        engine = CollisionRules(config,image_width=report['width_px'],image_height=report['height_px'],detector_imgsz=report['requested_imgsz'])
        frames = [json.loads(s) for s in Path(report['frame_cache']).read_text().splitlines()]
        # Source fingerprint selects evaluation labels only; engine never sees it.
        is_cadp = report['input_sha256'] == json.loads((ROOT/DEFAULT_REPORTS[0]).read_text())['input_sha256']
        expected_pair_by_frame = {}
        if is_cadp:
            for row in frames:
                index = row['frame_index']
                pair = []
                for ident in (0, 2):
                    gt = truth.get((index,ident))
                    objects = row['observations']
                    best = max(objects,key=lambda o:iou(gt,o['bbox_xyxy'])) if gt and objects else None
                    if best and iou(gt,best['bbox_xyxy']) >= .3 and best['track_id'] is not None:
                        pair.append(best['track_id'])
                if len(set(pair)) == 2:
                    expected_pair_by_frame[index] = sorted(pair)
        candidates = []
        with (output/f'{number:02d}_frames.jsonl').open('x') as stream:
            for row in frames:
                result = engine.update(row)
                stream.write(json.dumps(result,allow_nan=False)+'\n')
                if is_cadp and 96 <= row['frame_index'] <= 130:
                    pair = expected_pair_by_frame.get(row['frame_index'])
                    if pair and any(c['track_ids'] == pair for c in result['candidates']):
                        candidates.append(row['frame_index'])
        matched = []
        if is_cadp:
            matched = [e for e in engine.events if 96 <= e['frame_index'] <= 130 and e['track_ids'] == expected_pair_by_frame.get(e['frame_index'])]
        negative_review = any(f'MVI_{s}_tracking' in path.name for s in ('20011','20012','20032'))
        summary = dict(input_report=str(path.relative_to(ROOT)),input_report_sha256=sha256_file(path),input_sha256=report['input_sha256'],
                       frames=len(frames),events=engine.events,scope='development_diagnostic_not_locked_test',
                       verified_negative_sequence=negative_review,unlabelled_external_video=not is_cadp and not negative_review)
        if is_cadp:
            summary.update(reviewed_event_count=1,matched_events=min(1,len(matched)),missed_events=int(not matched),
                           extra_or_wrong_pair_events=len(engine.events)-min(1,len(matched)),
                           candidate_frames_in_gt_interval=len(candidates),gt_interval_frames=35,
                           candidate_event_recalled=bool(candidates),
                           first_alert_frame=matched[0]['frame_index'] if matched else None,
                           source_delay_seconds=None)
        elif negative_review:
            summary.update(false_alerts=len(engine.events),verified_negative_video_hours=report['processed_frames']/report['container_fps']/3600 if report['source_seconds_verified'] else None)
        summaries.append(summary)
    result = dict(checked_at=datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),
                  purpose='development_rule_error_analysis',config_sha256=sha256_file(output/'config.json'),
                  producer_sha256=sha256_file(ROOT/'src/collision_rules.py'),
                  rules_receive_ground_truth=False,test_set_evaluated=False,research_gate_satisfied=False,
                  source_fps_cadp_verified=False,summaries=summaries)
    save_json(output/'report.json',result)
    print(json.dumps([{k:v for k,v in r.items() if k != 'events'} | {'event_frames':[e['frame_index'] for e in r['events']]} for r in summaries],indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/collision_rules.json')
    parser.add_argument('--report',type=Path,action='append')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    evaluate(args.report or [ROOT/p for p in DEFAULT_REPORTS],json.loads(args.config.read_text()),args.output)
