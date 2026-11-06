"""Đánh giá cảnh báo theo sự kiện trên frame đã biết nhãn.

Đầu vào là dict chứa videos, events, samples và policy; đầu ra là alert,
ghép một-một và thống kê có phạm vi nhãn rõ ràng. Chạy qua
scripts/evaluate_events.py; không dùng kết quả này làm ground truth.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math


def _ratio(a, b):
    return a / b if b else None


def compare_matched_recall(first: dict, second: dict, tolerance: float = 0.0) -> dict:
    """So số FP khi hai kết quả cùng event và recall nằm trong tolerance.

    Hàm không chọn ngưỡng; caller phải khóa ngưỡng bằng validation riêng.
    """
    if not 0 <= tolerance <= 1:
        raise ValueError('Invalid recall tolerance')
    if first['censored'] or second['censored']:
        raise ValueError('Cannot compare censored events')
    if first.get('coverage_sha256') != second.get('coverage_sha256'):
        raise ValueError('Results require identical videos, GT and labeled frame coverage')
    if (first['policy']['version'], first['policy'].get('cooldown_frames', 0), first['policy'].get('post_onset_tolerance_frames')) != (second['policy']['version'], second['policy'].get('cooldown_frames', 0), second['policy'].get('post_onset_tolerance_frames')):
        raise ValueError('Results require the same alert policy')
    def event_set(result):
        return {(e['video_id'], e['event_id']) for e in result['matches'] + result['missed']}
    if event_set(first) != event_set(second) or not event_set(first):
        raise ValueError('Results need the same nonempty labeled events')
    r1, r2 = first['metrics']['recall'], second['metrics']['recall']
    same = abs(r1-r2) <= tolerance
    return {'recall_a': r1, 'recall_b': r2, 'matched_within_tolerance': same,
            'fp_a': first['metrics']['fp'] if same else None,
            'fp_b': second['metrics']['fp'] if same else None,
            'warning': 'Caller must also use identical videos, label coverage and alert policy.'}


def evaluate(data: dict, policy: dict) -> dict:
    """Replay điểm causal; chỉ đếm FP tại frame có nhãn negative/verified.

    Alert là cạnh chuyển từ OFF sang ON. Ghép theo thứ tự thời gian với event
    đã bắt đầu và chưa kết thúc, ưu tiên event kết thúc sớm nhất rồi event_id.
    Alert trước onset không được ghép; nếu vẫn ON tại onset thì event chưa
    thể kết luận FN chỉ từ cạnh alert, được ghi là censored.
    """
    threshold = float(policy['threshold'])
    cooldown = int(policy.get('cooldown_frames', 0))
    if not 0 <= threshold <= 1 or cooldown < 0 or not policy.get('version'):
        raise ValueError('Invalid alert policy')
    videos = {v['video_id']: v for v in data['videos']}
    if len(videos) != len(data['videos']):
        raise ValueError('Duplicate video ID')
    events = []
    event_ids = set()
    by_video = defaultdict(list)
    for raw_event in data.get('events', []):
        e = dict(raw_event)
        if e['video_id'] not in videos or e['event_id'] in event_ids:
            raise ValueError('Unknown video or duplicate event ID')
        event_ids.add(e['event_id'])
        v = videos[e['video_id']]
        if e.get('camera_id') != v.get('camera_id'):
            raise ValueError('Event camera does not match video')
        onset = e['onset_frame']
        if not isinstance(onset, int) or onset < 0:
            raise ValueError('Invalid event onset frame')
        if e.get('end_frame') is None:
            tolerance = policy.get('post_onset_tolerance_frames')
            if e.get('status') == 'verified' and (not isinstance(tolerance, int) or tolerance < 0):
                raise ValueError('Point-onset GT needs explicit nonnegative post-onset tolerance')
            e['end_frame'] = onset + (tolerance if e.get('status') == 'verified' else 0)
            e['window_kind'] = 'policy_window_from_point_onset'
        if not isinstance(e['end_frame'], int) or onset > e['end_frame'] or e.get('status') not in {'verified', 'unknown', 'ignore'} or not e.get('label_source'):
            raise ValueError('Invalid event interval, status or source')
        events.append(e)
        by_video[e['video_id']].append(e)
    rows = defaultdict(list)
    for row in data['samples']:
        if row['video_id'] not in videos or row.get('camera_id') != videos[row['video_id']].get('camera_id'):
            raise ValueError('Sample video/camera mismatch')
        score = float(row['score'])
        if not math.isfinite(score) or not 0 <= score <= 1 or not isinstance(row['frame'], int) or row['frame'] < 0:
            raise ValueError('Invalid frame or score')
        if row.get('label') not in {'negative', 'unknown', 'ignore', 'positive'} or not row.get('provenance'):
            raise ValueError('Missing label scope or prediction provenance')
        rows[row['video_id']].append(row)
    alerts, matches, missed, censored = [], [], [], []
    negative_clips = negative_alerts = 0
    eligible_seconds = 0.0
    for vid, video in videos.items():
        seq = rows[vid]
        if any(b['frame'] <= a['frame'] for a, b in zip(seq, seq[1:])):
            raise ValueError('Frames must be strictly increasing per video')
        verified = sorted((e for e in by_video[vid] if e['status'] == 'verified'), key=lambda e: (e['end_frame'], e['event_id']))
        used = set()
        prior_on = False
        previous = None
        last_alert = None
        video_alerts = []
        state = {}
        for row in seq:
            frame = row['frame']
            if previous is not None and frame != previous + 1:
                prior_on = False
                last_alert = None
            on = float(row['score']) > threshold
            state[frame] = on
            if on and not prior_on:
                alert = dict(video_id=vid, camera_id=video.get('camera_id'), frame=frame,
                             timestamp_s=row.get('timestamp_s'), score=float(row['score']),
                             provenance=row['provenance'], policy=policy['version'])
                if last_alert is not None and frame - last_alert <= cooldown:
                    alert['classification'] = 'suppressed_cooldown'
                else:
                    last_alert = frame
                    available = [e for e in verified if e['event_id'] not in used and e['onset_frame'] <= frame <= e['end_frame']]
                    ignored = row['label'] == 'ignore' or any(e['status'] == 'ignore' and e['onset_frame'] <= frame <= e['end_frame'] for e in by_video[vid])
                    if ignored:
                        alert['classification'] = 'unknown'
                    elif available:
                        e = available[0]
                        used.add(e['event_id'])
                        alert.update(classification='tp', event_id=e['event_id'])
                        match = dict(event_id=e['event_id'], video_id=vid, alert_frame=frame,
                                     onset_frame=e['onset_frame'], match_window_end_frame=e['end_frame'],
                                     window_kind=e.get('window_kind', 'author_event_interval'),
                                     label_source=e['label_source'], delay_frames=frame-e['onset_frame'], delay_seconds=None)
                        fps = video.get('source_fps')
                        if video.get('source_timing_verified') and fps and math.isfinite(float(fps)) and float(fps) > 0:
                            match['delay_seconds'] = match['delay_frames'] / float(fps)
                        matches.append(match)
                    elif any(e['status'] in {'unknown', 'ignore'} and e['onset_frame'] <= frame <= e['end_frame'] for e in by_video[vid]):
                        alert['classification'] = 'unknown'
                    elif row['label'] == 'negative' or (row['label'] == 'positive' and any(e['onset_frame'] <= frame <= e['end_frame'] for e in verified)):
                        alert['classification'] = 'fp'
                    else:
                        alert['classification'] = 'unknown'
                alerts.append(alert)
                video_alerts.append(alert)
            prior_on = on
            previous = frame
        for e in verified:
            if e['event_id'] in used:
                continue
            onset, end = e['onset_frame'], e['end_frame']
            early_active = state.get(onset, False) and (onset - 1 in state and state[onset - 1])
            ignored_frames = {r['frame'] for r in seq if r['label'] == 'ignore'}
            complete = all(frame in state and frame not in ignored_frames and not any(
                other['status'] == 'ignore' and other['onset_frame'] <= frame <= other['end_frame']
                for other in by_video[vid]) for frame in range(onset, end + 1))
            item = dict(video_id=vid, event_id=e['event_id'])
            if early_active or not complete:
                item['reason'] = 'active_before_onset' if early_active else 'missing_event_frames'
                censored.append(item)
                if early_active:
                    previous_alerts = [a for a in video_alerts if a['frame'] < onset and
                                       all(state.get(f, False) for f in range(a['frame'], onset+1))]
                    if previous_alerts:
                        previous_alerts[-1].setdefault('early_for_events', []).append(e['event_id'])
            else:
                missed.append(item)
        is_negative = video.get('fully_labeled_negative') is True
        if is_negative:
            if by_video[vid] or not seq or any(r['label'] != 'negative' for r in seq):
                raise ValueError('Negative clip needs complete negative labels and no event')
            start, end = video.get('first_frame'), video.get('last_frame')
            if start is None or end is None or len(seq) != end-start+1 or seq[0]['frame'] != start or seq[-1]['frame'] != end:
                raise ValueError('Negative clip frame coverage is incomplete')
            negative_clips += 1
            count = sum(a['classification'] == 'fp' for a in video_alerts)
            negative_alerts += count
            if video.get('duration_verified') and video.get('duration_seconds', 0) > 0:
                eligible_seconds += float(video['duration_seconds'])
    tp = len(matches)
    fp = sum(a['classification'] == 'fp' for a in alerts)
    fn = len(missed)
    precision, recall = _ratio(tp, tp+fp), _ratio(tp, tp+fn)
    f1 = _ratio(2*tp, 2*tp+fp+fn) if tp+fn else None
    timed_fp = sum(1 for a in alerts if a['classification'] == 'fp' and videos[a['video_id']].get('fully_labeled_negative') and videos[a['video_id']].get('duration_verified') and videos[a['video_id']].get('duration_seconds', 0) > 0)
    coverage = {'videos': sorted(data['videos'], key=lambda x: x['video_id']),
                'events': sorted(data.get('events', []), key=lambda x: (x['video_id'], x['event_id'])),
                'samples': sorted((dict(video_id=r['video_id'], camera_id=r.get('camera_id'),
                                        frame=r['frame'], label=r['label'], timestamp_s=r.get('timestamp_s'))
                                   for r in data['samples']), key=lambda x: (x['video_id'], x['frame']))}
    signature = hashlib.sha256(json.dumps(coverage, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    return dict(policy=policy, coverage_sha256=signature, metrics=dict(tp=tp, fp=fp, fn=fn, censored_events=len(censored),
                precision=precision, recall=recall, f1=f1,
                false_alerts_per_negative_clip=_ratio(negative_alerts, negative_clips),
                false_alerts_per_hour=_ratio(timed_fp * 3600, eligible_seconds),
                negative_clips=negative_clips, timed_negative_seconds=eligible_seconds,
                unknown_alerts=sum(a['classification'] == 'unknown' for a in alerts),
                early_alerts=sum(bool(a.get('early_for_events')) for a in alerts)),
                alerts=alerts, matches=matches, missed=missed, censored=censored,
                caveat='Censored events and unknown alerts excluded; incomplete labels limit interpretation.')
