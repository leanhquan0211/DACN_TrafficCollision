"""Create editable progress report and demo slides from actual project artifacts."""
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import sha256_file


def clean(value):
    return value.replace("**", "").replace("`", "")


def main():
    from docx import Document
    from docx.shared import Cm, Pt
    from pptx import Presentation
    from pptx.util import Inches, Pt as PPt
    from pptx.dml.color import RGBColor
    import cv2
    import numpy as np
    out=ROOT/"delivery";out.mkdir(exist_ok=True)
    assets=out/"assets";assets.mkdir(exist_ok=True)
    catalog=json.loads((ROOT/"configs/demo_catalog.json").read_text())
    runs=[]
    for sample in catalog["samples"]:
        for mode,path in sample["reports"].items():
            report=json.loads((ROOT/path).read_text())
            runs.append((sample,mode,path,report))
    cadp=next(row for row in runs if row[0]["id"]=="cadp-001407" and row[1]=="tracking")
    images=[]
    for path in (ROOT/cadp[0]["source"],(ROOT/cadp[2]).parent/Path(cadp[3]["output_video"]).name):
        cap=cv2.VideoCapture(str(path));cap.set(cv2.CAP_PROP_POS_FRAMES,110);ok,frame=cap.read();cap.release()
        if not ok:raise RuntimeError(f"Cannot extract illustration: {path}")
        images.append(cv2.resize(frame,(640,360)))
    compare=np.concatenate(images,axis=1)
    for x,label in ((15,"INPUT / frame 110"),(655,"YOLO + ByteTrack / frame 110")):
        cv2.putText(compare,label,(x,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),4)
        cv2.putText(compare,label,(x,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
    illustration=assets/"cadp_frame110.jpg";cv2.imwrite(str(illustration),compare)
    doc=Document()
    section=doc.sections[0];section.page_width=Cm(21);section.page_height=Cm(29.7);section.top_margin=Cm(2);section.bottom_margin=Cm(2);section.left_margin=Cm(2.5);section.right_margin=Cm(2)
    normal=doc.styles["Normal"];normal.font.name="Times New Roman";normal.font.size=Pt(12)
    normal.paragraph_format.line_spacing=1.25
    doc.core_properties.title="Báo cáo hiện trạng — Traffic Lab"
    doc.core_properties.author="Thông tin sinh viên chưa được cung cấp"
    doc.core_properties.subject="Bản demo vehicle inference; chưa nghiệm thu collision detection"
    lines=(ROOT/"docs/BAO_CAO_HIEN_TRANG.md").read_text().splitlines();i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith("| "):
            group=[]
            while i<len(lines) and lines[i].strip().startswith("|"):
                row=[clean(c.strip()) for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+",c) for c in row):group.append(row)
                i+=1
            table=doc.add_table(rows=1,cols=len(group[0]));table.style="Light Shading Accent 1"
            for j,value in enumerate(group[0]):table.rows[0].cells[j].text=value
            for row in group[1:]:
                cells=table.add_row().cells
                for j,value in enumerate(row):cells[j].text=value
            continue
        if line.startswith("# "):doc.add_heading(clean(line[2:]),0)
        elif line.startswith("## "):doc.add_heading(clean(line[3:]),1)
        elif line.startswith("- "):doc.add_paragraph(clean(line[2:]),style="List Bullet")
        else:doc.add_paragraph(clean(line))
        i+=1
    doc.add_heading("Phụ lục: ảnh chạy thật",1)
    doc.add_picture(str(illustration),width=Cm(16))
    doc.add_paragraph("CADP 001407, frame 110: ảnh sạch bên trái và YOLO/ByteTrack bên phải. Bbox/ID phương tiện không là kết luận va chạm.")
    screenshot=ROOT/"outputs/audits/delivery_2026-11-14/dashboard.png"
    if screenshot.exists():
        doc.add_picture(str(screenshot),width=Cm(16))
        doc.add_paragraph("Giao diện demo cục bộ. Các kết quả thực nghiệm cuối còn cần bổ sung theo kế hoạch.")
    doc.save(out/"BAO_CAO_HIEN_TRANG.docx")

    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    bg=RGBColor.from_string("0B1220");fg=RGBColor.from_string("EDF3FA");teal=RGBColor.from_string("5EE0BB");muted=RGBColor.from_string("B5C5D8")
    def text(slide,value,x,y,w,h,size=22,color=fg,bold=False):
        box=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
        tf=box.text_frame;tf.word_wrap=True
        for j,line in enumerate(value.split("\n")):
            p=tf.paragraphs[0] if j==0 else tf.add_paragraph();p.text=line;p.font.name="Arial";p.font.size=PPt(size);p.font.bold=bold;p.font.color.rgb=color;p.space_after=PPt(15)
        return box
    def slide(title,body="",note=""):
        s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=bg
        text(s,"TRAFFIC LAB / ĐỒ ÁN CHUYÊN NGÀNH",.65,.32,12,.4,11,teal,True)
        text(s,title,.65,1,12,1,30,fg,True)
        if body:text(s,body,.8,2.2,11.8,4.4,21,muted)
        text(s,f"NGUYÊN MẪU · CHƯA CÓ COLLISION CLASSIFIER                                    14.11.2026 / {len(prs.slides):02}",.65,7.05,12,.3,9,teal)
        if note:s.notes_slide.notes_text_frame.text=note
        return s
    slide("Phân tích phương tiện từ CCTV", "Nền tảng cho phát hiện và cảnh báo va chạm giao thông\nYOLOv8n · ByteTrack · Cache theo frame · Dashboard cục bộ\nSinh viên / MSSV / GVHD: điền trước khi nộp", "Mở đầu: trình bày đây là bản demo nền tảng, không nhận đã hoàn thành chức năng tai nạn.")
    slide("Bài toán và phạm vi", "• Mục tiêu đề tài: sự kiện va chạm xe–xe từ camera cố định.\n• Hiện có: phát hiện xe, ID tạm, đối chiếu và bằng chứng thủ công.\n• Chưa có: accident detector/verifier, cảnh báo tự động, event metrics.\n• Không suy va chạm từ bbox chồng nhau.")
    slide("Luồng xử lý đã triển khai", "Video sạch → YOLOv8n → ByteTrack → MP4 + JSONL + report\nGiao diện → job CPU riêng → kiểm hash/cache/MP4 → công bố kết quả\nMỗi run cô lập model/ID; missing có mask, không bịa bbox.\nReview thủ công tách khỏi ground truth và cảnh báo.")
    slide("Dữ liệu: bốn chuỗi, một sự kiện dương", "• CADP 001407: 221 ảnh; Colliding frame 96–130 do người rà.\n• DETRAC: 2.037 ảnh / ba chuỗi âm đã rà.\n• 35 vùng B0 mới là proposal; chưa split/train.\n• CADP 20 FPS là trình chiếu; source_time_s vẫn null.")
    table="\n".join(f"{s['id']} / {mode}: {r['processed_frames']} frame · {r['observation_count']:,} bbox · "+(f"{r['unique_track_ids']} ID tạm" if mode=="tracking" else "không ID") for s,mode,_,r in runs)
    slide("Kết quả chạy thật",table+"\nCác số trên mô tả output, không là accuracy hoặc F1.")
    s=slide("Xem đầu vào và kết quả tại frame 110")
    s.shapes.add_picture(str(illustration),Inches(.65),Inches(2.3),width=Inches(12))
    text(s,"Trái: ảnh gốc sạch. Phải: bbox/ID phương tiện. Chưa có kết luận va chạm của thuật toán.",.8,6.1,12,.7,17,muted)
    slide("Lỗi quan sát và giới hạn đo", "• Debug xe buýt: 13/35 frame class car; association chưa duyệt GT.\n• ID tạm có thể đổi; không báo IDF1 nếu chưa có mapping.\n• FPS là xử lý file offline trên CPU; chưa benchmark streaming/GPU.\n• Không có event precision/recall/F1, FAR/hour hoặc delay.")
    slide("Demo trực tiếp — 5 phút", "1. CADP: phát hai video, chọn frame, xem ID/class.\n2. Bấm chạy lại CPU để tạo output mới.\n3. Chuyển DETRAC để đối chiếu cảnh âm.\n4. Lưu nhận xét thủ công, mở ảnh, tải JSONL/report.\n5. Trình bày giới hạn và phần phải hoàn thiện.")
    slide("Kiểm chứng và bàn giao", "• Test nhãn, clock, missing, fingerprint, leakage và output.\n• HTTP: video Range, job thật, review JPEG, lỗi đầu vào.\n• Gói ZIP có source, trọng số, hai clip và bốn bộ kết quả.\n• Hướng dẫn cài/chạy, manifest SHA-256; không mang .venv.\n• Xem audit để biết kết quả kiểm; test pass không thay accuracy.")
    slide("Bốn tuần còn lại", "Tuần 1: nhãn + nhiều sự kiện + group split, chốt phạm vi với GV.\nTuần 2: B0/B1 và FP/FN sau khi đủ dữ liệu.\nTuần 3: candidates/rules/FSM nếu qua gate.\nTuần 4: test khóa, metrics, báo cáo và dựng lại demo.\nNếu thiếu dữ liệu: xin duyệt phạm vi hẹp sớm; không tạo số giả.")
    slide("Kết luận hiện tại", "Đã có nguyên mẫu vehicle inference chạy và trình diễn được.\nChức năng tự động phát hiện/cảnh báo va chạm chưa hoàn thành.\nƯu tiên tiếp theo: dữ liệu, nhãn và thí nghiệm baseline.\nNguồn/bằng chứng: README, XLSX, docs/INFERENCE_CACHE.md, report/hash và registry dữ liệu.")
    prs.save(out/"SLIDE_DEMO.pptx")
    record=dict(created_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                report_source="docs/BAO_CAO_HIEN_TRANG.md",report_source_sha256=sha256_file(ROOT/"docs/BAO_CAO_HIEN_TRANG.md"),
                artifact_paths=["delivery/BAO_CAO_HIEN_TRANG.docx","delivery/SLIDE_DEMO.pptx"],
                run_reports=[dict(path=path,sha256=sha256_file(ROOT/path)) for _,_,path,_ in runs],
                final_research_submission_ready=False)
    (out/"document_provenance.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print("Created delivery/BAO_CAO_HIEN_TRANG.docx and delivery/SLIDE_DEMO.pptx (11 slides)")


if __name__=="__main__":main()
