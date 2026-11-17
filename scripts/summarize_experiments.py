"""Build a provenance-checked metric ledger and figures; never substitutes demos for test metrics."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
from src.data_preparation import save_csv,save_json,sha256_file


def percent(value):
    return 'Không xác định' if value is None else f'{100*value:.2f}%'


def run(vehicle_path,b0_path,output):
    vehicle=json.loads(vehicle_path.read_text());b0=json.loads(b0_path.read_text())
    if not vehicle['complete'] or not b0['complete']:raise ValueError('Incomplete experiment')
    if vehicle['test_set_evaluated'] or b0['test_set_evaluated']:raise ValueError('Unexpected evaluation scope')
    if sha256_file(ROOT/'yolov8n.pt')!=vehicle['weights_sha256'] or sha256_file(ROOT/b0['checkpoint'])!=b0['checkpoint_sha256']:
        raise ValueError('Checkpoint fingerprint mismatch')
    for p,h in vehicle['code_sha256'].items():
        if sha256_file(ROOT/p)!=h:raise ValueError('Evaluation producer differs from report: '+p)
    if sha256_file(ROOT/'configs/vehicle_evaluation.json')!=vehicle['protocol_sha256']:
        raise ValueError('Evaluation protocol changed')
    if sha256_file(vehicle_path.parent/'image_manifest.json')!=vehicle['image_manifest_sha256']:
        raise ValueError('Evaluation image manifest changed')
    for profile in vehicle['profiles']:
        folder=vehicle_path.parent/profile
        metadata=json.loads((folder/'prediction_metadata.json').read_text())
        if sha256_file(folder/'predictions.jsonl')!=metadata['cache_sha256']:
            raise ValueError('Prediction cache fingerprint mismatch')
    output.mkdir(parents=True,exist_ok=False)
    rows=[]
    for profile,data in vehicle['profiles'].items():
        for task,metrics in data['results'].items():
            p=next(x for x in metrics['operating_points'] if x['confidence']==.25)
            rows.append(dict(model='yolov8n_COCO',profile=profile,task=task,split='development',
                images=vehicle['images'],confidence=.25,precision=p['precision'],recall=p['recall'],
                mAP50=metrics['mAP50'],mAP50_95=metrics['mAP50_95'],tp=p['tp'],fp=p['fp'],fn=p['fn']))
    save_csv(output/'vehicle_metrics.csv',rows,list(rows[0]))
    # Public summary contains only counts/metrics/provenance, no images or user uploads.
    summary=dict(schema_version=1,recorded_at=datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),
        purpose='research_metric_ledger_development_not_test',historical_snapshot_not_current_machine_inventory=True,
        vehicle=dict(weights='yolov8n.pt',weights_sha256=vehicle['weights_sha256'],
            publisher_train_data=vehicle['checkpoint_train_data'],local_fine_tuning_performed=False,
            evaluated_sequences=vehicle['protocol']['sequences'],images=vehicle['images'],source_boxes=vehicle['source_xml_boxes'],
            source_classes=vehicle['source_class_box_counts'],protocol=vehicle['protocol'],results=rows),
        b0=dict(checkpoint=b0['checkpoint'],checkpoint_sha256=b0['checkpoint_sha256'],
            base_weights_sha256=b0['base_weights_sha256'],dataset_counts=b0['dataset_counts'],
            scene_splits=b0['training_config']['scene_splits'],epochs=b0['training_config']['training']['epochs'],
            metrics=b0['metrics'],validation_fixed_operating_point=b0['validation_fixed_operating_point'],
            precision_recall_scope=b0['precision_recall_scope'],used_in_demo=False),
        event_evaluation=dict(independent_precision=None,independent_recall=None,mAP50=None,
            reason='No locked independently labelled event test; bbox AP is not event alert precision/recall'),
        independent_test_evaluated=False,research_gate_satisfied=False,training_performed_in_this_audit=False,
        limitations=vehicle['limitations']+b0['limitations'],
        source_reports=[dict(path=str(p.relative_to(ROOT)),sha256=sha256_file(p)) for p in (vehicle_path,b0_path)],
        producer_sha256=sha256_file(Path(__file__)))
    save_json(output/'summary.json',summary)
    lines=['# Kết quả thực nghiệm có nguồn gốc dữ liệu','',
        'Bản tổng hợp sau phản hồi ngày16/11, hoàn tất kiểm tra ngày17/11/2026. Các con số dưới đây được chạy trên máy phát triển; **chưa có test độc lập khóa trước phát triển**. Số test phần mềm, bbox và ID không phải accuracy mô hình.','',
        '## Train và đánh giá trên đâu?','',
        '| Thành phần | Train | Đánh giá | Trạng thái |','| --- | --- | --- | --- |',
        '| Detector xe trong demo | YOLOv8n COCO pretrained của nhà phát hành; chưa fine-tune xe trên dữ liệu đồ án | 2037ảnh DETRAC MVI_20011(664), MVI_20012(936), MVI_20032(437), nhãn XML nguồn | Development; đã dùng các cảnh này để phát triển, không gọi test |',
        '| B0 accident | 25ảnh: T-T_crash_1 và V-V_crash_0;19dương/6âm;12epoch | 18ảnh: T-T_crash_2 và V-V_crash_1;12dương/6âm | STTAD ví dụ tác giả, validation phát triển; không có test |',
        '| Cảnh báo B2 motion_contact_v5 | Luật thủ công sau detector, không phải model accident đã train | CADP/DETRAC đã dùng chỉnh luật | Chưa có precision/recall sự kiện độc lập |','',
        '[Nguồn YOLOv8 pretrained](https://docs.ultralytics.com/models/yolov8/), [nguồn DETRAC tác giả](https://sites.google.com/view/daweidu/projects/ua-detrac), [nguồn STTAD](https://github.com/ZTR02/STTAD). Metadata checkpoint xe cũng ghi `coco.yaml`. Không lấy mAP nhà phát hành làm kết quả đồ án.','',
        '## Detector xe: cùng checkpoint, cùng ảnh và protocol','',
        'P/R là micro tại **confidence0,25 / IoU0,50**; AP dùng điểm từ0,001, COCO101điểm, max100detection/ảnh.17.920bbox nguồn trước xử lý ignore. Vùng ignore XML và bbox truncation≥0,5 không là FP/FN bình thường; xem cấu hình để tái lập.','',
        '| Tác vụ | NMS | Precision@0,25 | Recall@0,25 | mAP50 | mAP50–95 | TP / FP / FN |',
        '| --- | --- | ---: | ---: | ---: | ---: | --- |']
    for r in rows:
        task='Định vị vehicle (1lớp)' if r['task']=='vehicle_localization' else 'Phân lớp car/bus (2lớp)'
        profile='Theo lớp — gốc' if r['profile']=='pretrained_class_aware_nms' else 'Giữa các lớp — demo mới'
        lines.append(f"| {task} | {profile} | {percent(r['precision'])} | {percent(r['recall'])} | {percent(r['mAP50'])} | {percent(r['mAP50_95'])} | {r['tp']} / {r['fp']} / {r['fn']} |")
    lines+=['','**Không gộp hai tác vụ:** định vị vehicle gộp mọi lớp xe nên không đo phân biệt car/truck/bus. Phép đo2lớp chỉ có car/bus dùng chung; van/others nguồn là vùng ignore, không ép others thànhtruck. Vì thế chưa có mAP lớp truck/xe máy đáng tin cậy từ phép đo này.','',
        'NMS giữa lớp giảm FP định vị nhưng làm mAP50 car/bus giảm90,60→87,32% (−3,28điểm phần trăm). Không kết luận NMS mới nâng accuracy phân lớp từ việc video bớt khung trùng. Chưa dùng kết quả development này để tuyên bố cải thiện trên camera độc lập.','',
        '## B0 accident: kiểm lại checkpoint đã train','',
        'Các P/R trong bảng này là điểm trên đường PR do Ultralytics chọn theo F1; **không cùng định nghĩa operating point0,25 của bảng xe**. Train chỉ để chẩn đoán, không là kết quả kiểm tổng quát hóa.','',
        '| Split | Precision đường PR | Recall đường PR | mAP50 | mAP50–95 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for split,m in b0['metrics'].items():
        lines.append(f"| {split} | {percent(m['metrics/precision(B)'])} | {percent(m['metrics/recall(B)'])} | {percent(m['metrics/mAP50(B)'])} | {percent(m['metrics/mAP50-95(B)'])} |")
    fixed=b0['validation_fixed_operating_point']
    lines+=['',f"Tại confidence0,25 / IoU0,50 trên validation: **TP={fixed['tp']}, FP={fixed['fp']}, FN={fixed['fn']}; precision không xác định vì không có dự đoán, recall0%, F1=0**. Không ghi precision100% từ FP=0. Model này chưa được đưa vào demo.",'',
        'mAP50 train83,24% nhưng validation1,21% cho thấy chưa chuyển được sang hai cảnh validation. Tập chỉ4cảnh ví dụ; nhãn âm do agent rà riêng12frame, chưa đối soát độc lập; phần thiếu nhãn không tự coi âm. Không dùng31frame dương để suy31sự kiện độc lập.','',
        '## Protocol và bằng chứng','',
        '- [Config cố định trước phép đo xe](../configs/vehicle_evaluation.json). Hai profile chỉ khác NMS, giữ model640/conf/IoU/maxDet và tập ảnh. Không dùng lớp hiển thị/vote ID để chấm metric detector.','- [Config huấn luyện B0](../configs/b0_feasibility.json), [quy trình/giới hạn B0](B0_FEASIBILITY.md). Giữ manifest/split/review/checkpoint cũ.','- [Snapshot số liệu đọc được sau clone](evidence/2026-11-17-evaluation.json). Raw GT/predictions, hash từng ảnh, report và PR curves/CSV vẫn cục bộ trong audit; snapshot không chứng minh asset có trên máy mới.','- [COCO API](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py) qua pycocotools2.0.11; đây là protocol development khai báo, **không phải official DETRAC benchmark**. Không báo FPS streaming từ chạy file/COCO cache.','',
        '```bash','.venv/bin/python -m pip install -r requirements-eval.txt',
        '.venv/bin/python -B scripts/audit_b0_checkpoint.py --output outputs/experiments/b0_audit_repeat',
        '.venv/bin/python -B scripts/evaluate_vehicle_detector.py --output outputs/experiments/vehicle_eval_repeat',
        '.venv/bin/python -B scripts/summarize_experiments.py \\','  --vehicle outputs/experiments/vehicle_eval_repeat/report.json \\',
        '  --b0 outputs/experiments/b0_audit_repeat/report.json \\','  --output outputs/experiments/summary_repeat','```','',
        'Cần đúng ảnh/trọng số/XML theo catalog. Archive XML12,8MB đã khôi phục/khớp SHA; không tải bộ ảnh đầy đủ. Lượt đầu lỗi serialize kiểu NumPy sau khi đã suy luận đủ2037ảnh; giữ cache/log/producer cũ, sửa serializer và kiểm lại bộ test. Resume chỉ nhận stream đầy đủ/cùngprotocol/cùngảnh và ghi hash, không bịa lại thời gian inference. Hai profile đều có prediction từng ảnh; lỗi công cụ không bị ghi thành kết quả model.','',
        '## Việc nghiên cứu còn thiếu','',
        '1. Chọn và kiểm dataset tai nạn CCTV có vùng/onset và negative đầy đủ; chốt quy tắc accident, uncertain và nhóm camera/sự kiện. Chưa đủ dữ liệu để gọi tập hiện tại là benchmark nghiên cứu.','2. Tách trọn nhóm camera/nguồn/sự kiện thành train/validation/test, loại bản cắt/trùng/gần trùng trước split. Toàn bộ clip đã dùng demo/chỉnh luật để ở development. Khóa test trước tuning; không chia frame liên tiếp ngẫu nhiên.','3. Train B0 trên dữ liệu đủ/đã rà với cấu hình cố định; chọn threshold/checkpoint bằng validation, so baseline trên cùng protocol. Không tăng epoch trên25ảnh rồi gọi là đã giải quyết tổng quát hóa.','4. Chấm detection bbox bằngP/R/AP, cảnh báo bằng eventP/R/F1/FAR/hour/delay; chỉ sau đó so B1/B2/MLP/GRU. Không dùng mAP xe để thay chất lượng phát hiện tai nạn.','',
        '**Chưa đạt điều kiện nghiệm thu độ chính xác hoặc hoàn thành gate nghiên cứu.**']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for task,axis in zip(('vehicle_localization','car_bus_common_classes'),axes):
        for profile,data in vehicle['profiles'].items():
            curve=data['results'][task]['pr_curve_iou50']
            import numpy as np
            values=np.array(list(curve['precision_by_class'].values()))
            axis.plot(curve['recall'],values.mean(axis=0),label=profile.replace('pretrained_','').replace('demo_',''))
        axis.set(title=task.replace('_',' '),xlabel='Recall',ylabel='Interpolated precision',xlim=(0,1),ylim=(0,1.02))
        axis.grid(alpha=.2);axis.legend(fontsize=7)
    fig.savefig(output/'vehicle_pr.png',dpi=180);fig.savefig(output/'vehicle_pr.pdf');plt.close(fig)
    fig,axis=plt.subplots(figsize=(6,4),layout='constrained')
    values=[b0['metrics'][s]['metrics/mAP50(B)']*100 for s in ('train','val')]
    bars=axis.bar(['Train (25 images)','Development val (18 images)'],values,color=['#4378bf','#c46853'])
    axis.bar_label(bars,fmt='%.2f%%');axis.set(ylabel='BBox mAP50 (%)',ylim=(0,100),title='B0 accident: training-scene fit vs validation')
    fig.savefig(output/'b0_train_val.png',dpi=180);fig.savefig(output/'b0_train_val.pdf');plt.close(fig)
    print(json.dumps(dict(summary=str(output/'summary.json'),rows=len(rows),independent_test=False),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vehicle',type=Path,required=True)
    parser.add_argument('--b0',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT/'outputs'):parser.error('Keep generated evidence below outputs/')
    run(args.vehicle.resolve(),args.b0.resolve(),args.output.resolve())
