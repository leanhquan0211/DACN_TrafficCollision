"""Phân tích lỗi bbox và các đoạn dự đoán B0 liên tiếp, không tự tạo nhãn.

Đầu vào: bbox/prediction đã đo hoặc score theo frame. Đầu ra: thống kê lỗi
và đoạn frame có dự đoán. Script analyze_b0.py gọi các hàm này sau train;
không chạy trực tiếp và không huấn luyện model trong module này.
"""
from __future__ import annotations

from collections import Counter
from collections import deque
import statistics
from scripts.train_b0 import iou, match_boxes


class CausalScoreFilter:
    """Giữ trạng thái B1 trong một video; reset khi đổi video hoặc có frame thiếu.

    B0 là score hiện tại > ngưỡng. k-of-N cần đủ cửa sổ rồi ít nhất k frame
    dương; EMA chỉ tích lũy quá khứ, khởi tạo0. Đầu ra là trạng thái scene,
    chưa phải sự kiện va chạm được xác minh hoặc xác suất đã hiệu chuẩn.
    """
    def __init__(self, threshold: float, k: int, n: int, alpha: float):
        if not 0<threshold<1 or not 1<=k<=n or not 0<alpha<=1:
            raise ValueError('Invalid causal filter parameters')
        self.threshold=threshold;self.k=k;self.n=n;self.alpha=alpha
        self.history=deque(maxlen=n);self.ema=0.0;self.previous=None

    def step(self, frame: int, score: float) -> dict:
        if not 0<=score<=1:raise ValueError('Invalid scene score')
        if self.previous is not None and frame<=self.previous:raise ValueError('Non-increasing source frame')
        if self.previous is not None and frame!=self.previous+1:
            self.history.clear();self.ema=0.0
        raw=score>self.threshold
        self.history.append(raw);self.ema=self.alpha*score+(1-self.alpha)*self.ema
        self.previous=frame
        return dict(b0_on=raw,kofn_on=len(self.history)==self.n and sum(self.history)>=self.k,
                    ema_on=self.ema>self.threshold,ema_score=self.ema,history_frames=len(self.history))


def positive_runs(frames: list[dict]) -> list[dict]:
    """Gom đúng các frame liên tiếp có bbox; một frame trống sẽ ngắt đoạn.

    Đây là cách ghi log B0 thô, không phải bộ lọc thời gian B1 hay alert đã
    xác nhận. Đánh số nguồn được giữ nguyên, không nối qua frame bị thiếu.
    """
    runs = []
    current = None
    previous = None
    for row in frames:
        index = int(row['source_frame'])
        if previous is not None and index <= previous:
            raise ValueError('Source frames must be strictly increasing')
        if current is not None and (not row['prediction_count'] or index != previous + 1):
            runs.append(current)
            current = None
        if row['prediction_count']:
            if current is None:
                current = dict(start_frame=index, end_frame_inclusive=index, frames=0,
                               peak_confidence=0.0)
            current['end_frame_inclusive'] = index
            current['frames'] += 1
            current['peak_confidence'] = max(current['peak_confidence'], float(row['max_confidence']))
        previous = index
    if current is not None:
        runs.append(current)
    return runs


def temporal_summary(frames: list[dict], intervals: list[dict], negative: bool) -> dict:
    """Chỉ tính trên phạm vi nhãn thật: toàn clip âm hoặc interval đã review.

    CADP có khoảng Colliding theo đối tượng nhưng chưa có vùng accident chuẩn
    B0. Chỉ báo số frame có bất kỳ bbox trong khoảng này; không gọi là bbox
    recall, không coi phần còn lại của clip là negative và không suy giây.
    """
    if negative and intervals:
        raise ValueError('Negative sequence cannot contain positive intervals')
    runs = positive_runs(frames)
    result = dict(frames=len(frames), frames_with_predictions=sum(bool(r['prediction_count']) for r in frames),
                  predicted_boxes=sum(int(r['prediction_count']) for r in frames), raw_positive_runs=runs)
    if negative:
        result['negative_frame_prediction_fraction'] = result['frames_with_predictions'] / len(frames) if frames else None
        result['false_raw_runs'] = len(runs)
    else:
        checked = []
        for event in intervals:
            start, end = int(event['start_frame']), int(event['end_frame_inclusive'])
            if start > end:
                raise ValueError('Invalid temporal interval')
            selected = [r for r in frames if start <= r['source_frame'] <= end]
            if len(selected) != end - start + 1:
                raise ValueError('Cannot evaluate an incomplete reviewed interval')
            hits = [r['source_frame'] for r in selected if r['prediction_count']]
            checked.append(dict(event_id=event['event_id'], start_frame=start, end_frame_inclusive=end,
                                reviewed_frames=len(selected), frames_with_any_bbox=len(hits),
                                first_bbox_frame=hits[0] if hits else None,
                                first_bbox_offset_frames=hits[0]-start if hits else None,
                                scope='temporal presence diagnostic; no spatial match or event precision'))
        result['reviewed_intervals'] = checked
        result['outside_intervals_label'] = 'unknown_not_negative'
    return result


def classify_case(case: dict, width: int, height: int, matching_iou: float) -> dict:
    """Giải thích FP theo hình học, không đoán nguyên nhân cảnh từ tên file.

    FP gần GT có thể là hộp lệch; FP xa GT có thể là đối tượng khác hoặc
    background. Chỉ người/AI xem ảnh mới phân biệt được nguyên nhân nội dung.
    """
    if min(width, height) <= 0:
        raise ValueError('Image dimensions must be positive')
    gt = case['gt_xyxy']
    used = {p['matched_gt'] for p in case['predictions'] if p['matched_gt'] is not None}
    counts = Counter()
    predictions = []
    for prediction in case['predictions']:
        overlap = max((iou(prediction['xyxy'], box) for box in gt), default=0.0)
        if prediction['matched_gt'] is not None:
            category = 'true_positive'
        elif not gt:
            category = 'false_positive_on_verified_negative'
        elif overlap >= matching_iou:
            category = 'duplicate_or_conflicting_prediction'
        elif overlap >= .1:
            category = 'localization_overlap_below_matching_iou'
        else:
            category = 'false_positive_disjoint_from_annotated_region'
        counts[category] += 1
        predictions.append(dict(**prediction, max_iou_any_gt=overlap, geometry_category=category))
    objects = []
    for index, box in enumerate(gt):
        area = max(0, box[2]-box[0]) * max(0, box[3]-box[1])
        objects.append(dict(gt_index=index, xyxy=box, matched=index in used,
                            image_area_fraction=area/(width*height),
                            min_side_pixels=min(box[2]-box[0], box[3]-box[1])))
    if len(used) != case['tp'] or len(gt)-len(used) != case['fn']:
        raise ValueError('Saved box matching and case totals disagree')
    return dict(width=width, height=height, categories=dict(counts), predictions=predictions, objects=objects)


def object_size_summary(cases: list[dict]) -> dict:
    """So diện tích tương đối GT được bắt/bỏ sót; chỉ là thống kê mô tả.

    Dùng phần trăm ảnh để không lẫn độ phân giải các nguồn. Không tự gọi GT
    là small/medium theo COCO vì các ngưỡng COCO dùng diện tích pixel khác.
    """
    result = {}
    for scope in sorted({case['scope'] for case in cases}):
        result[scope] = {}
        for matched in (True, False):
            values = [item['image_area_fraction']*100 for case in cases if case['scope']==scope
                      for item in case['objects'] if item['matched']==matched]
            result[scope]['matched' if matched else 'missed'] = dict(
                count=len(values), median_image_area_percent=statistics.median(values) if values else None)
    return result


def resized_size_counts(cases: list[dict], image_size: int) -> dict:
    """Đếm TP/FN theo cạnh ngắn bbox sau resize, không suy nguyên nhân từ kích thước.

    Letterbox giữ tỉ lệ theo cạnh dài; tăng imgsz giữ nhiều pixel hơn nhưng không
    phục hồi chi tiết đã mất ở ảnh gốc. Bin cố định giúp so lỗi trước khi train.
    """
    counts={key:{'matched':0,'missed':0} for key in ('below_16','16_to_32','32_to_64','at_least_64')}
    for case in cases:
        ratio=image_size/max(case['width'],case['height'])
        for item in case['objects']:
            side=item['min_side_pixels']*ratio
            key='below_16' if side<16 else '16_to_32' if side<32 else '32_to_64' if side<64 else 'at_least_64'
            counts[key]['matched' if item['matched'] else 'missed']+=1
    return counts


def confidence_metrics(cases: list[dict], confidence: float, matching_iou: float) -> dict:
    """Đo bbox tại một confidence từ cache; ghép lại sau lọc để không giữ TP cũ.

    Cache phải chỉ có frame có nhãn dương/âm rõ. Frame unknown không được biến
    thành âm. Dùng điều kiện score > ngưỡng như NMS của bản Ultralytics đã pin.
    Chỉ số ảnh âm có hộp và tổng hộp sai được đếm riêng, không là alert/giờ.
    """
    if not 0 <= confidence <= 1 or not 0 < matching_iou <= 1:
        raise ValueError('Invalid confidence or matching IoU')
    total=dict(tp=0,fp=0,fn=0)
    negatives=negative_hits=negative_boxes=0
    identities=set()
    for case in cases:
        identity=(case['source_sequence'],int(case['source_frame']))
        if identity in identities:raise ValueError('Duplicate frame in prediction cache')
        identities.add(identity)
        gt=case['gt_xyxy']
        if case['collision_label'] not in ('positive','negative') or bool(gt)!=(case['collision_label']=='positive'):
            raise ValueError('Unknown or inconsistent collision label')
        if any(not 0<=p['confidence']<=1 for p in case['predictions']):
            raise ValueError('Invalid cached prediction confidence')
        predictions=[dict(xyxy=p['xyxy'],confidence=p['confidence']) for p in case['predictions'] if p['confidence']>confidence]
        matched=match_boxes(gt,predictions,matching_iou)
        for key in total:total[key]+=matched[key]
        if not gt:
            negatives+=1;negative_hits+=bool(predictions);negative_boxes+=len(predictions)
    precision=total['tp']/(total['tp']+total['fp']) if total['tp']+total['fp'] else 0.0
    recall=total['tp']/(total['tp']+total['fn']) if total['tp']+total['fn'] else 0.0
    return dict(confidence=confidence,**total,precision=precision,recall=recall,
        f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
        negative_frames=negatives,negative_frames_with_predictions=negative_hits,
        negative_predicted_boxes=negative_boxes,
        negative_frame_prediction_fraction=negative_hits/negatives if negatives else None)


def choose_confidence(points: list[dict], minimum_recall: float) -> dict:
    """Chọn trên validation: đạt recall floor rồi tối đa F1, tie ít ảnh âm sai.

    Nếu không đạt floor thì báo không khả thi; không tự hạ tiêu chuẩn sau khi
    xem dữ liệu. Tập test/holdout không được đưa vào hàm lựa chọn này.
    """
    if not 0<=minimum_recall<=1:raise ValueError('Invalid recall floor')
    eligible=[p for p in points if p['recall']>=minimum_recall]
    if not eligible:raise ValueError('No validation confidence satisfies recall floor')
    return max(eligible,key=lambda p:(p['f1'],-p['negative_frames_with_predictions'],p['precision'],p['confidence']))


def require_unseen_negative_holdout(record: dict) -> None:
    """Chặn dùng lại holdout đã mở, kể cả lượt đo trước bị gián đoạn."""
    if record.get('model_predictions_seen') is not False or record.get('evaluation_status'):
        raise ValueError('Negative holdout has already been opened or reserved for evaluation')
    if not record.get('samples') or any(r.get('collision_label')!='negative' for r in record['samples']):
        raise ValueError('Holdout must contain author/review-backed negative samples only')


def hard_negative_indices(scores: list[float]) -> tuple[set[int],set[int]]:
    """20mốc đều và10mẫu khó rải theo thời gian; chỉ gọi cho clip train đã khóa."""
    if len(scores)<60 or any(not 0<=s<=1 for s in scores):raise ValueError('Need at least60 valid train scores')
    anchors={round(i*(len(scores)-1)/19) for i in range(20)}
    hard=set()
    for bin_index in range(10):
        eligible=[i for i in range(len(scores)) if i not in anchors and i*10//len(scores)==bin_index]
        if not eligible:raise ValueError('No candidate left in temporal mining bin')
        hard.add(max(eligible,key=lambda i:(scores[i],-i)))
    return anchors,hard


def filter_state_summary(records: list[dict], field: str, intervals: list[dict], negative: bool) -> dict:
    """Đếm trạng thái ON, không gọi trạng thái EMA/k-of-N là bbox vật lý."""
    transformed=[dict(r,prediction_count=int(r[field])) for r in records]
    measured=temporal_summary(transformed,intervals,negative)
    measured['active_frames']=measured.pop('frames_with_predictions')
    measured.pop('predicted_boxes')
    measured['raw_on_bouts']=measured.pop('raw_positive_runs')
    if negative:measured['negative_active_fraction']=measured.pop('negative_frame_prediction_fraction')
    for item in measured.get('reviewed_intervals',[]):
        item['active_frames']=item.pop('frames_with_any_bbox')
        item['first_active_frame']=item.pop('first_bbox_frame')
        item['first_active_offset_frames']=item.pop('first_bbox_offset_frames')
        item['active_before_reviewed_interval']=any(r[field] for r in records if r['source_frame']<item['start_frame'])
        item['scope']='scene-state presence in reviewed Colliding interval; not spatial/event recall or onset delay'
    measured['scope']='binary scene states; not physical bbox counts or confirmed event alerts'
    return measured
