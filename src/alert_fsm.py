"""FSM cảnh báo causal theo từng cặp track, giữ metadata frame làm evidence.

Đầu vào là video_id, frame và score theo cặp; đầu ra event mới và evidence
metadata sau số frame chờ. Dùng để kiểm hệ thống, chưa xác minh ngưỡng B2.
"""
from __future__ import annotations

from collections import deque
import math


class AlertFSM:
    """Tách cooldown theo cặp; gap/video mới kết thúc evidence chưa đủ hậu cảnh."""
    def __init__(self, config):
        self.cfg = config
        if not (0 <= config['low'] <= config['high'] <= 1 and config['confirm_frames'] >= 1 and
                config['cooldown_frames'] >= 0 and config['pre_frames'] >= 0 and config['post_frames'] >= 0):
            raise ValueError('Invalid FSM config')
        if 'rearm_low_frames' in config and (config['rearm_low_frames'] < 1 or config.get('missing_expire_frames', 30) < 1):
            raise ValueError('Invalid rearm/missing frame count')
        self.video = None
        self.previous = None
        self.counter = 0
        self.states = {}
        self.ring = deque(maxlen=config['pre_frames'] + 1)
        self.pending = []

    def step(self, video_id, frame, pairs):
        completed = []
        if video_id != self.video or (self.previous is not None and frame != self.previous+1):
            if video_id == self.video and self.previous is not None and frame <= self.previous:
                raise ValueError('Non-increasing frame')
            for event in self.pending:
                event['evidence_complete'] = False
                completed.append(event)
            self.pending.clear()
            self.states.clear()
            self.ring.clear()
        self.video, self.previous = video_id, frame
        normalized = {}
        for item in pairs:
            ids = tuple(sorted(item['track_ids']))
            score = float(item['score'])
            if len(ids) != 2 or ids[0] == ids[1] or ids in normalized or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError('Invalid pair or score')
            normalized[ids] = score
        frame_record = {'video_id': video_id, 'frame': frame, 'pairs': [dict(track_ids=list(k), score=v) for k, v in sorted(normalized.items())]}
        for event in list(self.pending):
            event['evidence_frames'].append(frame_record)
            if frame >= event['confirmation_frame'] + self.cfg['post_frames']:
                event['post_complete'] = True
                event['evidence_complete'] = event['pre_complete']
                self.pending.remove(event)
                completed.append(event)
        self.ring.append(frame_record)
        emitted = []
        for pair in sorted(set(self.states) | set(normalized)):
            score = normalized.get(pair, 0.0)
            state = self.states.setdefault(pair, {'state': 'idle', 'hits': 0, 'until': -1, 'low_frames': 0, 'missing_frames': 0})
            if state['state'] == 'cooldown':
                if 'rearm_low_frames' in self.cfg:
                    # Chỉ rearm sau tín hiệu thấp được quan sát liên tục;
                    # mất track không được tự xem là bằng chứng sự kiện kết thúc.
                    if pair not in normalized:
                        state['missing_frames'] += 1
                        state['low_frames'] = 0
                        if state['missing_frames'] >= self.cfg.get('missing_expire_frames', 30):
                            self.states.pop(pair, None)
                        continue
                    state['missing_frames'] = 0
                    state['low_frames'] = state['low_frames']+1 if score <= self.cfg['low'] else 0
                    if state['low_frames'] < self.cfg['rearm_low_frames']:
                        continue
                    state.update(state='idle', hits=0, low_frames=0)
                else:
                    if frame <= state['until']:
                        continue
                    state.update(state='idle', hits=0)
            if score >= self.cfg['high']:
                state['hits'] += 1
                state['state'] = 'suspected'
            elif score < self.cfg['low']:
                state.update(state='idle', hits=0)
            else:
                state['hits'] = 0
                if state['state'] != 'idle':
                    state['state'] = 'suspected'
            if state['hits'] >= self.cfg['confirm_frames']:
                self.counter += 1
                event = {'event_id': f'{video_id}:{frame}:{self.counter}', 'video_id': video_id,
                         'track_ids': list(pair), 'confirmation_frame': frame, 'score': score,
                         'policy_version': self.cfg['version'], 'state': 'confirmed',
                         'evidence_frames': list(self.ring),
                         'pre_complete': len(self.ring) == self.cfg['pre_frames']+1,
                         'post_complete': self.cfg['post_frames'] == 0,
                         'evidence_complete': self.cfg['post_frames'] == 0 and len(self.ring) == self.cfg['pre_frames']+1}
                emitted.append(event)
                if self.cfg['post_frames']:
                    self.pending.append(event)
                else:
                    completed.append(event)
                state.update(state='cooldown', hits=0, until=frame+self.cfg['cooldown_frames'])
            elif state['state'] == 'idle' and pair not in normalized:
                self.states.pop(pair, None)
        return {'emitted': emitted, 'completed': completed,
                'states': {str(k): v['state'] for k, v in self.states.items()}}

    def finish(self):
        """Kết thúc nguồn: đánh dấu evidence thiếu hậu cảnh thay vì giả đủ."""
        result = self.pending[:]
        for event in result:
            event['evidence_complete'] = False
        self.pending.clear()
        return result
