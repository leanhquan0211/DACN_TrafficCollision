"""Chuẩn bị cùng đầu vào cặp cho T0 MLP và B3/T1 GRU causal.

Đầu vào là frame/candidate từ B2; đầu ra vector, cửa sổ quá khứ và model
PyTorch chưa huấn luyện. Không tạo nhãn hay tự chia tập từ các dự đoán B2.
"""
from __future__ import annotations

from collections import deque
import math

FEATURE_NAMES = ('distance', 'approach', 'iou', 'speed_a', 'speed_b',
                 'speed_change_a', 'speed_change_b', 'direction_change_a',
                 'direction_change_b', 'age_a', 'age_b', 'confidence_a', 'confidence_b',
                 'velocity_a_valid', 'velocity_b_valid', 'motion_valid', 'history_a_valid',
                 'history_b_valid', 'direction_a_valid', 'direction_b_valid')


def pair_vector(frame_record, candidate):
    """Trả vector cố định; giá trị thiếu về 0 và có mask đi kèm."""
    lookup = {int(t['track_id']): t for t in frame_record['tracks']}
    a, b = (lookup[i] for i in candidate['track_ids'])
    def number(v):
        return float(v) if v is not None else 0.0
    return [number(v) for v in (candidate['distance_norm'], candidate['approach_per_frame'],
        candidate['iou'], a['speed_per_frame'], b['speed_per_frame'], a['speed_change_per_frame'],
        b['speed_change_per_frame'], a['direction_change_radians'], b['direction_change_radians'],
        a['track_age'], b['track_age'], a['confidence'], b['confidence'], a['velocity_valid'],
        b['velocity_valid'], candidate['motion_valid'], a['history_valid'], b['history_valid'],
        a['direction_change_radians'] is not None, b['direction_change_radians'] is not None)]


class CausalWindows:
    """Giữ lịch sử một video; frame/candidate gián đoạn tạo cửa sổ mới."""
    def __init__(self, length):
        if length < 1:
            raise ValueError('Window length must be positive')
        self.length = length
        self.history = {}
        self.video = None
        self.last_frame = None

    def step(self, record):
        video, frame = record['video_id'], record['frame']
        if video != self.video or (self.last_frame is not None and frame != self.last_frame+1):
            if video == self.video and self.last_frame is not None and frame <= self.last_frame:
                raise ValueError('Frames must increase')
            self.history.clear()
        self.video, self.last_frame = video, frame
        active = set()
        result = []
        for candidate in record['candidates']:
            key = tuple(candidate['track_ids'])
            if key in active:
                raise ValueError('Duplicate pair')
            active.add(key)
            history = self.history.setdefault(key, deque(maxlen=self.length))
            history.append((frame, pair_vector(record, candidate)))
            padding = self.length-len(history)
            result.append({'video_id': video, 'frame': frame, 'track_ids': list(key),
                           'features': [[0.0]*len(FEATURE_NAMES) for _ in range(padding)] + [v for _, v in history],
                           'window_frame_indices': [None]*padding + [i for i, _ in history],
                           'observation_mask': [0]*padding + [1]*len(history)})
        self.history = {k: v for k, v in self.history.items() if k in active}
        return result


def make_model(kind, input_size=len(FEATURE_NAMES)+1, hidden_size=32):
    """Tạo MLP hoặc GRU một chiều; nhận mask quan sát như một feature.

    MLP nhận tensor [batch, features]; GRU nhận [batch, time, features].
    Trả logits chưa sigmoid. Trọng số mặc định ngẫu nhiên, không dùng báo metric.
    """
    import torch
    import torch.nn as nn
    from torch.nn.utils.rnn import pack_sequence
    if kind == 'mlp':
        return nn.Sequential(nn.Linear(input_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 1))
    if kind == 'gru':
        class CausalGRU(nn.Module):
            def __init__(self):
                super().__init__()
                self.gru = nn.GRU(input_size, hidden_size, batch_first=True, bidirectional=False)
                self.head = nn.Linear(hidden_size, 1)
            def forward(self, x):
                # Input cuối cùng là mask quan sát. Bỏ phần padding bên trái
                # trước GRU để bias tại frame giả không ảnh hưởng hidden state.
                if x.ndim != 3 or x.shape[-1] != input_size:
                    raise ValueError('GRU input must be [batch,time,features]')
                mask = x[:, :, -1]
                if not torch.all((mask == 0) | (mask == 1)):
                    raise ValueError('Observation mask must be binary')
                if not torch.all(mask.sum(dim=1) > 0) or torch.any(mask[:, 1:] < mask[:, :-1]):
                    raise ValueError('Expected nonempty left-padded observation masks')
                packed = pack_sequence([x[i][mask[i].bool()] for i in range(x.shape[0])], enforce_sorted=False)
                _, hidden = self.gru(packed)
                return self.head(hidden[-1])
        return CausalGRU()
    raise ValueError('kind must be mlp or gru')


def validate_group_split(splits):
    """Từ chối group nguồn xuất hiện ở nhiều split; không tự tạo split."""
    owner = {}
    for split, groups in splits.items():
        for group in groups:
            if group in owner and owner[group] != split:
                raise ValueError(f'Group leakage: {group}')
            owner[group] = split


class TrainScaler:
    """Tính mean/std từ train; caller chỉ truyền các vector có mask hợp lệ."""
    def __init__(self):
        self.mean = None
        self.std = None

    def fit(self, vectors, *, split):
        if split != 'train' or not vectors or any(len(row) != len(FEATURE_NAMES) for row in vectors):
            raise ValueError('Scaler requires nonempty train vectors with the expected schema')
        if any(not math.isfinite(float(x)) for row in vectors for x in row):
            raise ValueError('Non-finite feature')
        # Thống kê chỉ tính quan sát hợp lệ; cột mask nhị phân giữ nguyên.
        numeric = 13
        masks = {1: 15, 3: 13, 4: 14, 5: 16, 6: 17, 7: 18, 8: 19}
        self.mean, self.std = [], []
        for i in range(numeric):
            values = [float(row[i]) for row in vectors if i not in masks or row[masks[i]] == 1]
            mean = sum(values)/len(values) if values else 0.0
            std = (sum((x-mean)**2 for x in values)/len(values))**0.5 if values else 1.0
            self.mean.append(mean)
            self.std.append(std or 1.0)
        self.mean += [0.0]*7
        self.std += [1.0]*7
        return self

    def transform(self, vector):
        if self.mean is None or len(vector) != len(FEATURE_NAMES):
            raise ValueError('Scaler not fitted or invalid vector')
        result = [(float(x)-m)/s for x, m, s in zip(vector, self.mean, self.std)]
        for i, mask in {1: 15, 3: 13, 4: 14, 5: 16, 6: 17, 7: 18, 8: 19}.items():
            if not vector[mask]:
                result[i] = 0.0
        return result

    def state(self):
        if self.mean is None:
            raise ValueError('Scaler not fitted')
        return {'feature_names': list(FEATURE_NAMES), 'mean': self.mean, 'std': self.std, 'fit_split': 'train'}

    @classmethod
    def from_state(cls, state):
        if state.get('feature_names') != list(FEATURE_NAMES) or state.get('fit_split') != 'train':
            raise ValueError('Scaler schema or fit split mismatch')
        mean, std = state.get('mean', []), state.get('std', [])
        if len(mean) != len(FEATURE_NAMES) or len(std) != len(FEATURE_NAMES) or any(not math.isfinite(float(x)) for x in mean+std) or any(float(x) <= 0 for x in std):
            raise ValueError('Invalid scaler state')
        obj = cls()
        obj.mean, obj.std = list(mean), list(std)
        return obj
