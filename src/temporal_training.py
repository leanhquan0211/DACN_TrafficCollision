"""Kiểm dữ liệu và huấn luyện MLP/GRU từ feature cache có nhãn đã xác minh.

Chỉ train/val theo nhóm nguồn; dữ liệu test không đi vào module. Chạy lệnh
scripts/train_temporal_verifier.py sau khi có release thật đã qua readiness.
"""
from __future__ import annotations

import math
from src.temporal_verifiers import FEATURE_NAMES, TrainScaler


def validate_records(records, window_frames):
    """Từ chối nhãn chưa xác minh, mask sai hoặc rò video/camera/event/group."""
    if not records or window_frames < 1:
        raise ValueError('Empty release or invalid window size')
    owners = {k: {} for k in ('group_id', 'video_id', 'camera_id', 'source_event_id')}
    groups = {'train': set(), 'val': set()}
    labels = {'train': set(), 'val': set()}
    for row in records:
        split = row.get('split')
        if split not in groups or row.get('label_status') != 'verified' or row.get('label') not in (0, 1):
            raise ValueError('Only verified binary train/val labels allowed')
        if not row.get('group_id') or not row.get('video_id') or not row.get('label_source'):
            raise ValueError('Missing source group, video or label provenance')
        if row['label'] == 1 and not row.get('source_event_id'):
            raise ValueError('Positive candidate needs verified source event ID')
        scope = row.get('label_frame_interval')
        if not isinstance(scope, list) or len(scope) != 2 or not all(isinstance(x, int) and x >= 0 for x in scope) or scope[0] > scope[1]:
            raise ValueError('Each verified label needs a valid source frame interval')
        values, mask = row.get('features', []), row.get('observation_mask', [])
        frame_indices = row.get('window_frame_indices', [])
        if len(values) != window_frames or len(mask) != window_frames or mask[-1] != 1 or any(x not in (0, 1) for x in mask):
            raise ValueError('Invalid window or observation mask')
        if any(b < a for a, b in zip(mask, mask[1:])):
            raise ValueError('Window must have left-only padding; internal missing requires explicit quality features')
        if any(len(v) != len(FEATURE_NAMES) or any(not math.isfinite(float(x)) for x in v) for v in values):
            raise ValueError('Feature schema mismatch or non-finite value')
        if any(any(x not in (0, 1) for x in v[-7:]) for v, valid in zip(values, mask) if valid):
            raise ValueError('Feature quality masks must be binary')
        if len(frame_indices) != window_frames or not isinstance(row.get('frame'), int) or row['frame'] < 0:
            raise ValueError('Missing window frame provenance')
        if not scope[0] <= row['frame'] <= scope[1]:
            raise ValueError('Window endpoint is outside verified label coverage')
        if any((index is not None) != bool(valid) for index, valid in zip(frame_indices, mask)):
            raise ValueError('Padding mask and frame indices disagree')
        observed = [i for i in frame_indices if i is not None]
        if any(not isinstance(i, int) or i < 0 for i in observed) or observed[-1] != row['frame'] or any(b != a+1 for a, b in zip(observed, observed[1:])):
            raise ValueError('Window frames must be contiguous, causal and end at frame')
        for field, mapping in owners.items():
            value = row.get(field)
            if value is None or value == '':
                continue
            if value in mapping and mapping[value] != split:
                raise ValueError(f'{field} appears in multiple splits')
            mapping[value] = split
        groups[split].add(row['group_id'])
        labels[split].add(row['label'])
    if any(not groups[s] or labels[s] != {0, 1} for s in groups):
        raise ValueError('Train and val each require independent groups and both verified classes')
    return {'train_records': sum(r['split'] == 'train' for r in records),
            'val_records': sum(r['split'] == 'val' for r in records),
            'train_groups': len(groups['train']), 'val_groups': len(groups['val'])}


def make_examples(records):
    """Fit scaler chỉ trên train rồi trả tensor-list cùng schema cho MLP/GRU."""
    train_vectors = [v for r in records if r['split'] == 'train'
                     for v, valid in zip(r['features'], r['observation_mask']) if valid]
    scaler = TrainScaler().fit(train_vectors, split='train')
    examples = []
    for r in records:
        window = [(scaler.transform(v) if valid else [0.0]*len(FEATURE_NAMES)) + [float(valid)]
                  for v, valid in zip(r['features'], r['observation_mask'])]
        examples.append({'split': r['split'], 'label': int(r['label']), 'window': window,
                         'video_id': r['video_id'], 'group_id': r['group_id'], 'frame': r.get('frame')})
    return scaler, examples
