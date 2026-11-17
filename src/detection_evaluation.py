"""DETRAC XML adapter and standard COCO bbox evaluation, separate from inference."""
from collections import Counter
import contextlib
import io
import math
import xml.etree.ElementTree as ET

SOURCE_CLASSES = {'car', 'bus', 'van', 'others'}


def xml_box(node):
    box = [float(node.attrib[k]) for k in ('left', 'top', 'width', 'height')]
    if not all(math.isfinite(x) for x in box) or min(box[2:]) <= 0:
        raise ValueError('Invalid source annotation box')
    return box  # Preserve source coordinates, including truncated/outside boxes.


def parse_detrac(data, sequence, expected_frames):
    root = ET.fromstring(data)
    if root.attrib.get('name') != sequence:
        raise ValueError('Annotation sequence mismatch')
    regions = [xml_box(b) for b in root.findall('ignored_region/box')]
    frames = []
    for number, frame in enumerate(root.findall('frame'), 1):
        if int(frame.attrib['num']) != number:
            raise ValueError('Missing, duplicate or unordered source frame')
        objects, seen = [], set()
        for target in frame.findall('target_list/target'):
            ident = int(target.attrib['id'])
            attributes = target.find('attribute').attrib
            name = attributes['vehicle_type'].lower()
            truncation = float(attributes['truncation_ratio'])
            if ident in seen or name not in SOURCE_CLASSES or not math.isfinite(truncation) or not 0 <= truncation <= 1:
                raise ValueError('Duplicate target or unsupported source class/truncation')
            seen.add(ident)
            objects.append(dict(source_id=ident, source_class=name, truncation=truncation,
                                bbox=xml_box(target.find('box'))))
        frames.append(dict(source_frame=number, objects=objects, ignored_regions=regions))
    if len(frames) != expected_frames:
        raise ValueError('Image/annotation frame count mismatch')
    return frames


def coco_truth(frames, task, truncation_ignore_from=.5):
    if task not in {'vehicle_localization', 'car_bus_common_classes'}:
        raise ValueError('Unsupported evaluation task')
    names = {1: 'vehicle'} if task == 'vehicle_localization' else {2: 'car', 5: 'bus'}
    result = dict(info={'description': 'Development subset, not official DETRAC benchmark'},
                  images=[{k: f[k] for k in ('id', 'file_name', 'width', 'height')} for f in frames],
                  categories=[dict(id=k, name=v) for k, v in names.items()], annotations=[])

    def add(frame, box, category, crowd, source_class=None):
        result['annotations'].append(dict(id=len(result['annotations'])+1, image_id=frame['id'],
            category_id=category, bbox=list(box), area=box[2]*box[3], iscrowd=int(crowd),
            source_vehicle_type=source_class))

    for frame in frames:
        for obj in frame['objects']:
            category = 1 if task == 'vehicle_localization' else {'car': 2, 'bus': 5}.get(obj['source_class'])
            if category is not None and obj['truncation'] < truncation_ignore_from:
                add(frame, obj['bbox'], category, False, obj['source_class'])
            else:
                for key in names:
                    add(frame, obj['bbox'], key, True, obj['source_class'])
        for box in frame['ignored_regions']:
            for key in names:
                add(frame, box, key, True)
    return result


def task_predictions(predictions, task):
    return [dict(p, category_id=1 if task == 'vehicle_localization' else p['category_id'])
            for p in predictions if task == 'vehicle_localization' or p['category_id'] in (2, 5)]


def evaluate_coco(truth, predictions, thresholds=(.1, .25), image_ids=None):
    """Use COCO's score-ordered matching, crowd handling and 101-point AP.

    P/R below are micro counts at fixed confidence, not max-F1 curve points.
    """
    import numpy as np
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        gt = COCO(); gt.dataset = truth; gt.createIndex()
        if predictions:
            dt = gt.loadRes(predictions)
        else:
            dt = COCO(); dt.dataset = dict(images=truth['images'], categories=truth['categories'], annotations=[]); dt.createIndex()
        evaluator = COCOeval(gt, dt, 'bbox')
        evaluator.params.imgIds = sorted(image_ids if image_ids is not None else gt.getImgIds())
        evaluator.params.maxDets = [1, 10, 100]
        evaluator.evaluate(); evaluator.accumulate(); evaluator.summarize()
    precision = evaluator.eval['precision'][:, :, :, 0, -1]

    def mean_valid(array):
        valid = array[array >= 0]
        return float(valid.mean()) if len(valid) else None

    entries = [e for e in evaluator.evalImgs if e is not None and e['aRng'] == evaluator.params.areaRng[0]]

    def fixed(threshold, category=None):
        selected = [e for e in entries if category is None or e['category_id'] == category]
        tp = fp = ignored = positives = 0
        for entry in selected:
            keep = np.asarray(entry['dtScores']) >= threshold
            ignore = entry['dtIgnore'][0].astype(bool)
            matched = entry['dtMatches'][0] > 0
            tp += int((keep & ~ignore & matched).sum())
            fp += int((keep & ~ignore & ~matched).sum())
            ignored += int((keep & ignore).sum())
            positives += int((~entry['gtIgnore'].astype(bool)).sum())
        fn = positives-tp
        if fn < 0:
            raise ValueError('More true positives than evaluated objects')
        return dict(confidence=threshold, iou=.5, tp=tp, fp=fp, fn=fn, ignored_predictions=ignored,
                    precision=tp/(tp+fp) if tp+fp else None, recall=tp/positives if positives else None,
                    f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)

    categories = {c['id']: c['name'] for c in truth['categories']}
    result = dict(mAP50=mean_valid(precision[0]), mAP50_95=mean_valid(precision),
        operating_points=[fixed(t) for t in thresholds],
        classes=[dict(category_id=int(category), name=categories[category], AP50=mean_valid(precision[0, :, i]),
                      AP50_95=mean_valid(precision[:, :, i]), operating_points=[fixed(t, category) for t in thresholds])
                 for i, category in enumerate(evaluator.params.catIds)],
        pr_curve_iou50=dict(recall=evaluator.params.recThrs.tolist(),
            precision_by_class={categories[c]: precision[0, :, i].tolist() for i,c in enumerate(evaluator.params.catIds)}),
        metric_backend='pycocotools bbox', images=len(evaluator.params.imgIds), max_detections_per_image=100)
    return result, log.getvalue()
