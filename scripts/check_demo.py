"""HTTP acceptance checks for the local demo; optional actual inference/review."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def check(base, *, run_inference=False, save_review=False):
    checks=[]
    def request(path, data=None, headers=None, status=200, raw=False):
        body=json.dumps(data).encode() if data is not None else None
        req=Request(base+path,data=body,headers=headers or {})
        try:
            with urlopen(req,timeout=30) as response:
                actual=response.status;payload=response.read();response_headers=dict(response.headers)
        except HTTPError as exc:
            actual=exc.code;payload=exc.read();response_headers=dict(exc.headers)
        if actual != status:
            raise AssertionError(f"{path}: HTTP {actual}, expected {status}: {payload[:200]}")
        return (payload,response_headers) if raw else json.loads(payload)
    catalog=request("/api/catalog")
    assert catalog["collision_detection_implemented"] is True
    assert catalog['collision_experimental'] is True
    assert not catalog["errors"],catalog["errors"]
    assert len(catalog["samples"])>=2
    checks.append("catalog_two_samples_without_asset_errors")
    request("/",raw=True);request("/app.js",raw=True);request("/style.css",raw=True)
    checks.append("html_js_css_http200")
    for sample in catalog["samples"]:
        for mode,run_id in sample["runs"].items():
            run=request("/api/run?id="+run_id)
            assert run["verified"] and run["report"]["mode"]==mode
            last=run["report"]["processed_frames"]-1
            frame=request(f"/api/frame?id={run_id}&index={last}")
            assert frame["frame_index"]==last
            if not run["report"]["source_seconds_verified"]:
                assert frame["source_time_s"] is None
            payload,headers=request(f"/media?id={run_id}&kind=output",headers={"Range":"bytes=0-31"},status=206,raw=True)
            assert len(payload)==32 and b"ftyp" in payload
            assert headers["Content-Range"].startswith("bytes 0-31/")
            request(f"/media?id={run_id}&kind=output",headers={"Range":"bytes=999999999-"},status=416,raw=True)
            checks.append(f"{sample['id']}_{mode}_report_last_frame_video_range")
            if mode == 'collision':
                assert run['report']['collision_experimental'] is True
                assert run['report']['event_count'] == len(run['events'])
                manifest=request(f'/download?id={run_id}&kind=events')
                assert manifest['experimental'] and not manifest['score_is_probability']
                assert len(manifest['events']) == len(run['events'])
                for event in run['events']:
                    prefix=f'/collision-evidence?run={run_id}&event={event["event_id"]}'
                    image,_=request(prefix+'&kind=snapshot',raw=True)
                    assert image.startswith(b'\xff\xd8')
                    clip,_=request(prefix+'&kind=clip',headers={'Range':'bytes=0-31'},status=206,raw=True)
                    assert b'ftyp' in clip
                request(f'/collision-evidence?run={run_id}&event=missing&kind=clip',status=400)
                checks.append(f"{sample['id']}_automatic_event_json_snapshot_clip_and_unknown_id")
    request("/api/jobs",dict(sample_id="cadp-001407",mode="tracking"),status=403)
    headers={"X-Demo-Token":catalog["token"],"Content-Type":"application/json"}
    request("/api/jobs",dict(sample_id="cadp-001407",mode="tracking"),headers={**headers,"Origin":"https://example.invalid"},status=403)
    request("/api/catalog",headers={"Host":"attacker.invalid"},status=403)
    request("/../../../etc/passwd",status=404)
    checks.append("unknown_paths_and_cross_origin_mutations_rejected")
    run_id=catalog["samples"][0]["runs"]["tracking"]
    if run_inference:
        job=request("/api/jobs",dict(sample_id="cadp-001407",mode="tracking"),headers=headers,status=202)
        request("/api/jobs",dict(sample_id="cadp-001407",mode="tracking"),headers=headers,status=400)
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            current=request("/api/job")["job"]
            if current["status"] not in {"running","validating"}:
                assert current["status"]=="complete",current
                assert current["id"]==job["id"]
                run_id=current["run_id"]
                run=request("/api/run?id="+run_id)
                assert run["report"]["processed_frames"]==221
                break
            time.sleep(.5)
        else:
            raise AssertionError("Inference timeout")
        checks.append("actual_cpu_job_221_frames_and_single_job_lock")
    if save_review:
        review=request("/api/reviews",dict(run_id=run_id,frame_index=110,note="Kiểm thử chức năng lưu bằng chứng; không là nhãn hoặc kết luận va chạm."),headers=headers,status=201)
        assert review["method"]=="manual_review" and not review["automatic_collision_alert"]
        assert not review["training_ground_truth"] and review["source_time_s"] is None
        image,_=request(f"/evidence?run={run_id}&review={review['id']}",raw=True)
        assert image.startswith(b"\xff\xd8")
        assert any(r["id"]==review["id"] for r in request("/api/reviews?id="+run_id))
        request("/api/reviews",dict(run_id=run_id,frame_index=-1,note="bad"),headers=headers,status=400)
        checks.append("manual_review_real_jpeg_and_invalid_frame_rejection")
    return dict(checked_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),url=base,
                passed=True,checks=checks,actual_inference=run_inference,manual_review_test=save_review,
                collision_accuracy_measured=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://127.0.0.1:8765")
    parser.add_argument("--run-inference",action="store_true")
    parser.add_argument("--save-review",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=check(args.url,run_inference=args.run_inference,save_review=args.save_review)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
