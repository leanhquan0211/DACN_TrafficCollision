"""Causal display labels; never overwrite raw detector classes or create GT."""
from collections import defaultdict, deque
import math


class VehicleLabels:
    def __init__(self, config):
        self.config = dict(config)
        for key in ('history_frames', 'maximum_track_gap_frames', 'minimum_support_observations'):
            value = config[key]
            if type(value) is not int or value < 1:
                raise ValueError('Invalid vehicle label window/support')
        if config['minimum_support_observations'] > config['history_frames']:
            raise ValueError('Vehicle label support exceeds window')
        for key in ('minimum_class_confidence', 'minimum_vote_share', 'scene_cut_mean_difference'):
            value = config[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError('Invalid vehicle label threshold')
        if (type(config['agnostic_nms']) is not bool
                or type(config['maximum_box_scale_ratio']) not in (int, float)
                or not math.isfinite(config['maximum_box_scale_ratio'])
                or config['maximum_box_scale_ratio'] < 1):
            raise ValueError('Invalid vehicle inference policy')
        self.tracks, self.next_frame = {}, 0

    def update(self, index, objects, *, scene_cut=False):
        if index != self.next_frame:
            raise ValueError('Vehicle labels require consecutive frames')
        self.next_frame += 1
        cfg = self.config
        if scene_cut:
            self.tracks.clear()
        self.tracks = {ident: state for ident, state in self.tracks.items()
                       if index - state['last'] <= cfg['maximum_track_gap_frames']}
        result = []
        for raw in objects:
            item = dict(raw)
            ident, box = raw['track_id'], raw['bbox_xyxy']
            history = deque()
            if ident is not None:
                state = self.tracks.get(ident)
                if state:
                    previous = state['box']
                    scale = max(max(a / b, b / a) for a, b in zip(
                        (box[2]-box[0], box[3]-box[1]),
                        (previous[2]-previous[0], previous[3]-previous[1])))
                    if scale <= cfg['maximum_box_scale_ratio']:
                        history = state['history']
                while history and index-history[0][0] >= cfg['history_frames']:
                    history.popleft()
            history.append((index, raw['class_name'], raw['confidence']))
            if ident is not None:
                self.tracks[ident] = dict(last=index, box=list(box), history=history)
            votes = defaultdict(float)
            strong = [h for h in history if h[2] >= cfg['minimum_class_confidence']]
            for _, name, confidence in strong:
                votes[name] += confidence
            winner = max(votes, key=votes.get) if votes else None
            share = votes[winner]/sum(votes.values()) if votes else 0.0
            name, status = None, 'uncertain'
            if ident is not None and len(strong) >= cfg['minimum_support_observations']:
                if share >= cfg['minimum_vote_share']:
                    name, status = winner, 'stabilized'
            elif raw['confidence'] >= cfg['minimum_class_confidence']:
                name, status = raw['class_name'], 'tentative'
            item['display_class'] = dict(name=name, status=status,
                support_observations=len(strong), vote_share=share, method=cfg['policy_id'])
            result.append(item)
        return result


def draw_vehicle_labels(frame, objects):
    """Render the same display label used by the table; det is the raw score."""
    import cv2
    image = frame.copy()
    for item in objects:
        label = item['display_class']
        name = label['name'] or 'vehicle'
        if label['status'] != 'stabilized':
            name += '?'
        prefix = f"id:{item['track_id']} " if item['track_id'] is not None else ''
        text = f"{prefix}{name} det:{item['confidence']:.2f}"
        x1, y1, x2, y2 = map(round, item['bbox_xyxy'])
        color = (185, 220, 94) if label['status'] == 'stabilized' else (80, 195, 245)
        cv2.rectangle(image, (x1,y1), (x2,y2), color, 2)
        (width,height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, .45, 1)
        x = min(max(0,x1),max(0,image.shape[1]-width-5))
        y = max(height+4,y1-4)
        cv2.rectangle(image,(x,y-height-3),(x+width+4,y+baseline),color,-1)
        cv2.putText(image,text,(x+2,y),cv2.FONT_HERSHEY_SIMPLEX,.45,(25,25,25),1,cv2.LINE_AA)
    return image
