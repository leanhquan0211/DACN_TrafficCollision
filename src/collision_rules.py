"""Causal experimental collision rules; no GT, filename, camera ID or future input.

Scores are evidence strengths, never calibrated collision probabilities.
All displacement features use bbox diagonals and source frame differences.
"""
from collections import deque
from itertools import combinations
import math
import statistics


def center(box):
    return ((box[0]+box[2])/2, (box[1]+box[3])/2)


def diagonal(box):
    return math.hypot(box[2]-box[0], box[3]-box[1])


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def interaction(a, b):
    inter = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    area = min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))
    gap = math.hypot(max(0, a[0]-b[2], b[0]-a[2]), max(0, a[1]-b[3], b[1]-a[3]))
    return inter/area if area > 0 else 0, gap/max(1, (diagonal(a)+diagonal(b))/2)


def velocity(history, end, window):
    points = [p for p in history if end-window <= p[0] <= end]
    if len(points) < 3 or points[-1][0]-points[0][0] < window-1:
        return None
    steps = []
    for a, b in zip(points, points[1:]):
        dt = b[0]-a[0]
        ca, cb = center(a[1]), center(b[1])
        scale = max(1, (diagonal(a[1])+diagonal(b[1]))/2)
        steps.append(((cb[0]-ca[0])/dt/scale, (cb[1]-ca[1])/dt/scale))
    return tuple(statistics.median(v[i] for v in steps) for i in (0, 1))


class CollisionRules:
    def __init__(self, config, *, image_width=640, image_height=640, detector_imgsz=640):
        self.config = dict(config)
        if min(image_width,image_height,detector_imgsz) <= 0:
            raise ValueError('Invalid collision input image size')
        bottom_limit = config.get('maximum_bottom_edge_gap_min_height')
        if bottom_limit is not None and (not isinstance(bottom_limit, (int, float))
                                        or isinstance(bottom_limit, bool)
                                        or not math.isfinite(bottom_limit) or bottom_limit <= 0):
            raise ValueError('Invalid bottom-edge compatibility limit')
        self.detector_scale = detector_imgsz/max(image_width,image_height)
        if (not 1 <= config['confirmation_hits'] <= config['confirmation_window_frames']
                or config['history_frames'] < config['minimum_history_frames']
                or config['minimum_history_frames'] < config['past_motion_offset_frames']+config['motion_window_frames']):
            raise ValueError('Invalid collision rule history/confirmation configuration')
        self.tracks = {}
        self.pairs = {}
        self.events = []
        self.next_frame = 0
        self.last_video_time = None
        self.segment = 0

    def reset_history(self):
        self.tracks.clear()
        self.pairs.clear()
        self.segment += 1

    def update(self, frame, *, scene_cut=False):
        cfg = self.config
        index = frame['frame_index']
        if index != self.next_frame:
            raise ValueError('Collision input must be consecutive and zero-based')
        video_time = frame['video_time_s']
        if not math.isfinite(video_time) or (self.last_video_time is not None and video_time <= self.last_video_time):
            raise ValueError('Collision input requires a monotonic video clock')
        self.next_frame += 1
        self.last_video_time = video_time
        if scene_cut:
            self.reset_history()
        current = {}
        for item in frame['observations']:
            ident = item['track_id']
            box = item['bbox_xyxy']
            if (ident is None or item.get('missing_mask', 0) or item['confidence'] < cfg['minimum_confidence']
                    or min(box[2]-box[0], box[3]-box[1]) < cfg['minimum_box_side_px']
                    or min(box[2]-box[0], box[3]-box[1])*self.detector_scale < cfg.get('minimum_box_side_inference_px',0)):
                continue
            if ident in current:
                raise ValueError('Duplicate observed track ID')
            history = self.tracks.get(ident)
            if history and (index-history[-1][0] > cfg['maximum_track_gap_frames']
                            or max(diagonal(box)/diagonal(history[-1][1]), diagonal(history[-1][1])/diagonal(box)) > cfg['maximum_box_scale_ratio']):
                history = None
                # Discontinuous IDs must not inherit pair confirmation/cooldown.
                for pair in list(self.pairs):
                    if ident in pair:
                        del self.pairs[pair]
            if history is None:
                history = deque(maxlen=cfg['history_frames'])
                self.tracks[ident] = history
            history.append((index, list(box), item['confidence']))
            current[ident] = item
        for ident in list(self.tracks):
            if index-self.tracks[ident][-1][0] > cfg['candidate_expiry_frames']:
                del self.tracks[ident]
        candidates = []
        new_events = []
        for pair in combinations(sorted(current), 2):
            a, b = (current[k]['bbox_xyxy'] for k in pair)
            overlap, gap = interaction(a, b)
            if gap > cfg['candidate_gap_body_units']:
                continue
            state = self.pairs.setdefault(pair, dict(hits=deque(maxlen=cfg['confirmation_window_frames']), last=index, cooldown_until=-1, state='idle'))
            state['last'] = index
            features = self.features(pair, index, overlap)
            hit = features is not None and features['contact'] and features['new_contact'] and features['approach'] and features['motion_change']
            state['hits'].append((index, bool(hit)))
            state['hits'] = deque(((i, h) for i, h in state['hits'] if index-i < cfg['confirmation_window_frames']), maxlen=cfg['confirmation_window_frames'])
            enough = sum(h for _, h in state['hits']) >= cfg['confirmation_hits']
            if index < state['cooldown_until']:
                state['state'] = 'cooldown'
            elif enough and hit:
                state['state'] = 'confirmed_by_rule'
                box = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                event = dict(event_id=f"event-{len(self.events)+1:04d}", method=cfg['rule_id'],
                             decision='suspected_collision', automatic=True, needs_review=True,
                             segment=self.segment, frame_index=index, video_time_s=video_time,
                             source_time_s=frame.get('source_time_s'), track_ids=list(pair), bbox_xyxy=box,
                             evidence_score=round(features['evidence_score'], 4), score_is_probability=False,
                             features=features, first_support_frame=min(i for i, h in state['hits'] if h))
                self.events.append(event)
                new_events.append(event)
                state['cooldown_until'] = index+cfg['pair_cooldown_frames']
                state['hits'].clear()
            else:
                state['state'] = 'suspected' if any(h for _, h in state['hits']) else 'idle'
            candidates.append(dict(track_ids=list(pair), state=state['state'], intersection_over_min=overlap,
                                   gap_body_units=gap, support=bool(hit), features=features))
        for pair in list(self.pairs):
            if index-self.pairs[pair]['last'] > cfg['candidate_expiry_frames']:
                del self.pairs[pair]
        return dict(frame_index=index, video_time_s=video_time, source_time_s=frame.get('source_time_s'),
                    scene_cut=scene_cut, segment=self.segment, candidates=candidates, new_events=new_events,
                    quality=dict(observations=len(frame['observations']),eligible_tracks=len(current),
                                 abstained_observations=len(frame['observations'])-len(current)))

    def features(self, pair, index, overlap):
        cfg = self.config
        histories = [self.tracks[k] for k in pair]
        if any(index-h[0][0] < cfg['minimum_history_frames'] for h in histories):
            return None
        if any(statistics.median(p[2] for p in h) < cfg['minimum_history_median_confidence'] for h in histories):
            return None
        window = cfg['motion_window_frames']
        old = [velocity(h, index-cfg['past_motion_offset_frames'], window) for h in histories]
        now = [velocity(h, index, window) for h in histories]
        if any(v is None for v in old+now):
            return None
        old_speed = [math.hypot(*v) for v in old]
        now_speed = [math.hypot(*v) for v in now]
        stop = [p >= cfg['minimum_prior_speed_body_per_frame'] and q <= p*cfg['stop_speed_ratio'] for p, q in zip(old_speed, now_speed)]
        turn = [p >= cfg['minimum_prior_speed_body_per_frame'] and q >= cfg['minimum_turn_speed_body_per_frame'] and
                (a[0]*b[0]+a[1]*b[1])/max(1e-12, p*q) <= cfg['direction_change_cosine']
                for a, b, p, q in zip(old, now, old_speed, now_speed)]
        shared = sorted(set(p[0] for p in histories[0]) & set(p[0] for p in histories[1]))
        past = [f for f in shared if f <= index-cfg['past_motion_offset_frames']]
        if not past:
            return None
        source_frame = past[0]
        before = [next(p[1] for p in h if p[0] == source_frame) for h in histories]
        current = [h[-1][1] for h in histories]
        scale = max(1, statistics.mean(diagonal(b) for b in current))
        closing = (distance(*map(center, before))-distance(*map(center, current)))/scale
        prior_overlap = interaction(*before)[0]
        # Partial image overlap can place a distant vehicle inside a foreground
        # box. Compare lower edges at the scale of the smaller vehicle instead
        # of treating that overlap plus braking as physical contact. This is a
        # conservative image-space gate, not a calibrated road-plane estimate.
        smaller_height = max(1, min(box[3]-box[1] for box in current))
        bottom_gap = abs(current[0][3]-current[1][3])/smaller_height
        bottom_limit = cfg.get('maximum_bottom_edge_gap_min_height')
        bottom_compatible = bottom_limit is None or bottom_gap <= bottom_limit
        overlap_contact = overlap >= cfg['contact_intersection_over_min']
        flags = dict(contact=overlap_contact and bottom_compatible,
                     new_contact=overlap-prior_overlap >= cfg['contact_increase'],
                     approach=closing >= cfg['approach_body_units'], motion_change=any(stop) or any(turn))
        return dict(**flags, evidence_score=sum(bool(v) for v in flags.values())/4,
                    overlap_contact=overlap_contact, bottom_edge_compatible=bottom_compatible,
                    bottom_edge_gap_min_height=bottom_gap,
                    overlap=overlap, prior_overlap=prior_overlap, approach_body_units=closing,
                    prior_speed_body_per_frame=old_speed, current_speed_body_per_frame=now_speed,
                    sudden_stop=stop, direction_change=turn, comparison_frame=source_frame)
