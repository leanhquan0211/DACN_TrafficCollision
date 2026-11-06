"""Tạo đặc trưng quỹ đạo và điểm luật B2 từ track observations từng frame.

Mỗi lời gọi step là một frame theo thứ tự; output là tracks và các cặp gần,
đang tiếp cận hoặc chồng hộp. Đơn vị chuyển động là tọa độ ảnh/frame, không
phải km/h. Dùng từ scripts/run_b2_motion.py, không train trong module này.
"""
from __future__ import annotations

import itertools
import math


def _iou(a, b):
    x = max(0, min(a[2], b[2])-max(a[0], b[0]))
    y = max(0, min(a[3], b[3])-max(a[1], b[1]))
    inter = x*y
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union > 0 else 0.0


class MotionFeatures:
    """Trạng thái chỉ thuộc một nguồn; frame thiếu thì reset lịch sử."""
    def __init__(self, config):
        self.cfg = config
        self.history = {}
        self.previous_frame = None

    def step(self, frame, observations):
        if self.previous_frame is not None and frame <= self.previous_frame:
            raise ValueError('Frames must be strictly increasing')
        if self.previous_frame is not None and frame != self.previous_frame + 1:
            self.history.clear()
        self.previous_frame = frame
        seen, tracks = set(), []
        for obs in observations:
            ident = int(obs['track_id'])
            if ident in seen:
                raise ValueError('Duplicate track ID in frame')
            seen.add(ident)
            box = [float(v) for v in obs['bbox_norm']]
            if len(box) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in box) or box[0] >= box[2] or box[1] >= box[3]:
                raise ValueError('Invalid normalized bbox')
            conf = float(obs['confidence'])
            if not math.isfinite(conf) or not 0 <= conf <= 1:
                raise ValueError('Invalid confidence')
            point = ((box[0]+box[2])/2, (box[1]+box[3])/2)
            old = self.history.get(ident)
            valid = bool(old and old['frame'] == frame-1)
            vx, vy = (point[0]-old['point'][0], point[1]-old['point'][1]) if valid else (None, None)
            speed = math.hypot(vx, vy) if valid else None
            prior_velocity_valid = bool(valid and old['speed'] is not None)
            change = abs(speed-old['speed']) if prior_velocity_valid else None
            direction = None
            if prior_velocity_valid and speed > 1e-6 and old['speed'] > 1e-6:
                cos = (vx*old['vx']+vy*old['vy'])/(speed*old['speed'])
                direction = math.acos(max(-1.0, min(1.0, cos)))
            age = old['age']+1 if valid else 1
            track = dict(track_id=ident, class_name=obs['class_name'], confidence=conf,
                         bbox_norm=box, center_norm=list(point), size_norm=[box[2]-box[0], box[3]-box[1]],
                         observed=True, velocity_valid=valid, history_valid=prior_velocity_valid,
                         vx_per_frame=vx, vy_per_frame=vy, speed_per_frame=speed,
                         speed_change_per_frame=change, direction_change_radians=direction, track_age=age)
            self.history[ident] = dict(frame=frame, point=point, vx=vx, vy=vy, speed=speed, age=age)
            tracks.append(track)
        # Không nội suy ID bị mất; lần quan sát sau gap được đánh dấu thiếu lịch sử.
        missing_ids = sorted(k for k, v in self.history.items() if v['frame'] == frame-1 and k not in seen)
        self.history = {k: v for k, v in self.history.items() if v['frame'] >= frame-1}
        roi = self.cfg['roi_normalized_xyxy']
        tracks_in_roi = [t for t in tracks if t['track_age'] >= self.cfg['min_track_age'] and roi[0] <= t['center_norm'][0] <= roi[2] and roi[1] <= t['center_norm'][1] <= roi[3]]
        tracks_in_roi.sort(key=lambda t: (-t['confidence'], t['track_id']))
        tracks_capped = len(tracks_in_roi) > self.cfg['max_tracks_for_pairs']
        tracks_in_roi = tracks_in_roi[:self.cfg['max_tracks_for_pairs']]
        pairs = []
        for a, b in itertools.combinations(tracks_in_roi, 2):
            dx = b['center_norm'][0]-a['center_norm'][0]
            dy = b['center_norm'][1]-a['center_norm'][1]
            distance = math.hypot(dx, dy)
            # Hai bbox lớn có thể giao nhau dù tâm cách xa hơn ngưỡng.
            # Config cũ giữ đúng hành vi lịch sử để replay có thể đối chiếu.
            overlap = _iou(a['bbox_norm'], b['bbox_norm'])
            if distance > self.cfg['max_normalized_distance'] and not (self.cfg.get('overlap_bypasses_distance', False) and overlap > 0):
                continue
            valid = a['velocity_valid'] and b['velocity_valid'] and distance > 1e-9
            rvx = b['vx_per_frame']-a['vx_per_frame'] if valid else None
            rvy = b['vy_per_frame']-a['vy_per_frame'] if valid else None
            approach = -(dx*rvx+dy*rvy)/distance if valid else None
            if not ((approach is not None and approach >= self.cfg['min_approach_per_frame']) or overlap > 0):
                continue
            speed_signal = any(t['speed_change_per_frame'] is not None and t['speed_change_per_frame'] >= self.cfg['min_speed_change_per_frame'] for t in (a, b))
            direction_signal = any(t['direction_change_radians'] is not None and t['direction_change_radians'] >= self.cfg['min_direction_change_radians'] for t in (a, b))
            signals = dict(overlap=overlap > 0, approaching=bool(approach is not None and approach >= self.cfg['min_approach_per_frame']), speed_change=speed_signal, direction_change=direction_signal)
            pairs.append(dict(track_ids=sorted([a['track_id'], b['track_id']]), distance_norm=distance,
                              relative_velocity_norm_per_frame=[rvx, rvy], approach_per_frame=approach,
                              iou=overlap, motion_valid=valid, signals=signals,
                              rule_score=sum(signals.values())/4,
                              meaning='heuristic suspicion, not collision probability'))
        pairs.sort(key=lambda p: (p['distance_norm'], p['track_ids']))
        total = len(pairs)
        return dict(frame=frame, tracks=tracks, missing_track_ids=missing_ids,
                    candidates=pairs[:self.cfg['max_candidates']],
                    candidate_count_before_cap=total, candidate_cap_reached=total > self.cfg['max_candidates'],
                    track_cap_reached=tracks_capped)
