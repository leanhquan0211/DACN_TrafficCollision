"""Build a dated, factual development report; does not overwrite the old thesis snapshot."""
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import sha256_file


def main():
    from docx import Document
    from docx.shared import Inches,Pt
    folder=ROOT/'delivery/collision_2026-11-16'
    folder.mkdir(exist_ok=False)
    audit=ROOT/'outputs/audits/collision_2026-11-16'
    replay=json.loads((audit/'final_replay/report.json').read_text())
    cadp=replay['summaries'][0]
    doc=Document();doc.styles['Normal'].font.name='Arial';doc.styles['Normal'].font.size=Pt(11)
    doc.add_heading('BÁO CÁO PHÁT TRIỂN PHÁT HIỆN VA CHẠM',0)
    doc.add_paragraph('Traffic Lab — cập nhật 16/11/2026. Bản thử nghiệm kỹ thuật, chưa phải kết quả nghiệm thu nghiên cứu.')
    doc.add_heading('1. Chức năng đã triển khai',1)
    doc.add_paragraph('MP4 tải lên → YOLOv8n phát hiện xe → ByteTrack → luật chuyển động causal → xác nhận nhiều frame/chống lặp theo cặp → cảnh báo nghi va chạm, khung đỏ, ảnh, clip và Events JSON. Runtime không đọc GT, tên video, camera ID hoặc frame va chạm biết trước.')
    doc.add_paragraph('B0 ảnh khả thi trước đó bỏ sót12/12 vùng validation tại confidence0,25. Theo yêu cầu mới, triển khai B2 luật/FSM song song để có sản phẩm vận hành. Giữ nguyên nhãn, split, review và gate nghiên cứu; chưa triển khai verifier MLP/GRU.')
    doc.add_heading('2. Cấu hình và cách hiểu',1)
    for text in [
        'Cần xe có ID và cạnh bbox ngắn ≥32pixel tại tỷ lệ đầu vào detector; xe nhỏ/xa có thể bị bỏ khỏi phân tích.',
        'Lịch sử32 quan sát; cửa sổ vận tốc4frame; so với12frame trước; chỉ dùng quá khứ và hiện tại.',
        'Kết hợp tiếp cận, tương tác không gian tăng, biến đổi tốc độ/hướng; xác nhận3/5frame, cooldown100frame theo cặp.',
        'Điểm bằng chứng không là xác suất. Cảnh báo mang suspected_collision và needs_review=true.',
        'CADP chưa biết FPS nguồn: frame109=5,45giây video trình chiếu20FPS, không báo delay nguồn hoặc tốc độ km/h.',
    ]:doc.add_paragraph(text,style='List Bullet')
    doc.add_heading('3. Kết quả development đã đo',1)
    table=doc.add_table(rows=1,cols=3);table.style='Table Grid'
    for c,t in zip(table.rows[0].cells,['Dữ liệu','Phạm vi','Kết quả']):c.text=t
    rows=[('CADP001407','221frame; interval96–130 đã rà',f"{cadp['matched_events']}/1 sự kiện, đúng cặp tại frame{cadp['first_alert_frame']}; ứng viên34/35frame"),
          ('DETRAC3chuỗi','2037frame≈81,48giây đã rà âm','0cảnh báo trong lượt cuối; đã dùng chỉnh luật'),
          ('Cao tốc Roboflow','250frame upload; chưa có GT','0cảnh báo; không tự gọi TN hoặc đo accuracy'),
          ('Kiểm phần mềm','70test; HTTP/Firefox/CPU/upload','Đạt; ảnh/clip/JSON có hash, refresh/restart giữ kết quả')]
    for row in rows:
        for c,t in zip(table.add_row().cells,row):c.text=t
    doc.add_paragraph('Không có test khóa độc lập. Không suy accuracy/F1=100% từ một sự kiện đã dùng phát triển;0FP trên81,48giây không chứng minh FAR/hour trên camera mới.')
    doc.add_heading('4. Lịch sử lỗi và sửa có bằng chứng',1)
    for version in ('v1','v2','v3','v4'):
        r=json.loads((audit/f'rules_{version}/report.json').read_text());s=r['summaries']
        fp=sum(x.get('false_alerts',0) for x in s)
        doc.add_paragraph(f"{version}: CADP bắt{s[0]['matched_events']}/1, cảnh báo sai CADP{s[0]['extra_or_wrong_pair_events']}; cảnh báo trên DETRAC âm={fp}.")
    doc.add_paragraph('Các FP ở v3 nằm chủ yếu trên bbox nhỏ/xa, che khuất và dao động. Lọc độ phân giải bbox ở v4 làm giảm FP trên development, đổi lại có nguy cơ bỏ sót va chạm xa. Chưa được kết luận tổng quát.')
    doc.add_page_break();doc.add_heading('5. Giao diện và bằng chứng thật',1)
    doc.add_picture(str(audit/'collision_dashboard.png'),width=Inches(6.2))
    doc.add_paragraph('Cảnh báo tự động frame109, ID tracker1/19; tách riêng khỏi nhận xét thủ công.')
    doc.add_heading('6. Chạy demo và công việc còn lại',1)
    doc.add_paragraph('Chạy bash demo.sh, mở http://127.0.0.1:8765, chọn Phát hiện va chạm · Thử nghiệm. Có thể tải MP4 H.264 tối đa100MiB/2phút/FullHD; nên720p trên CPU. Danh sách sự kiện chỉ có sau khi file đã xử lý/kiểm xong; chưa phải livestream.')
    doc.add_paragraph('Cần thêm sự kiện/camera độc lập, hard negatives/near miss, timestamp nguồn, split khóa trước chỉnh ngưỡng và đánh giá video dài. Giữ B0/bbox CADP ở trạng thái nghiên cứu chưa nghiệm thu; các gói ngày14/11 là snapshot trước cảnh báo.')
    doc.add_heading('Tài liệu và tái lập',1)
    doc.add_paragraph('docs/COLLISION_DETECTION.md; configs/collision_rules.json; scripts/run_collision.py; scripts/evaluate_collision_rules.py; scripts/check_inference_outputs.py. Toàn bộ số đo lấy từ audit cục bộ, không lấy metric paper làm kết quả project.')
    doc.add_paragraph('Tham khảo phương pháp: Ghahremannezhad et al. (IST2022), https://arxiv.org/abs/2208.06461; Zhang et al. (ByteTrack, ECCV2022), https://arxiv.org/abs/2110.06864. Không tuyên bố tái lập các paper.')
    output=folder/'BAO_CAO_PHAT_HIEN_VA_CHAM.docx';doc.save(output)
    provenance=dict(created_at=datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),purpose='development_report_not_final_thesis',
                    document_sha256=sha256_file(output),sources={str(p.relative_to(ROOT)):sha256_file(p) for p in [audit/'final_replay/report.json',audit/'browser_check.json',audit/'tests.log',ROOT/'configs/collision_rules.json',audit/'collision_dashboard.png']})
    (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(output)


if __name__=='__main__':main()
