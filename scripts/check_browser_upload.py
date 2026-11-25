"""Exercise real browser ONNX inference, upload lifecycle and v5 rule parity."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.collision_rules import CollisionRules


def close(a, b):
    if isinstance(a, dict):
        assert set(a) == set(b), (set(a), set(b))
        for k in a: close(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b): close(x, y)
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-8), (a, b)
    else:
        assert a == b, (a, b)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--video", type=Path, default=Path("data_samples/cadp/cadp_001407_clean_display20fps.mp4"))
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    assert output.is_relative_to(ROOT / "outputs")
    output.mkdir(parents=True, exist_ok=True)
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.support.ui import Select, WebDriverWait
    options = Options()
    options.add_argument("-headless")
    binary = Path("/snap/firefox/current/usr/lib/firefox/firefox")
    options.binary_location = str(binary) if binary.exists() else "/usr/bin/firefox"
    profiles = output / "profiles"
    profiles.mkdir(exist_ok=True)
    os.environ["SE_CACHE_PATH"] = str(ROOT / ".cache/selenium")
    service_options = dict(executable_path="/snap/bin/geckodriver") if Path("/snap/bin/geckodriver").exists() else {}
    service = Service(**service_options, log_output=str(output / "webdriver.log"),
                      service_args=["--profile-root", str(profiles)])
    driver = webdriver.Firefox(options=options, service=service)
    driver.set_script_timeout(30)
    checks = []
    try:
        driver.set_window_size(1450, 1050)
        driver.get(args.url)
        wait = WebDriverWait(driver, 180)
        get = lambda name: driver.find_element(By.ID, name)
        wait.until(lambda d: d.execute_script("return !!window.TrafficCore"))
        cfg = json.loads((ROOT / "configs/collision_rules.json").read_text())

        def obj(ident, x, y=100, conf=.8):
            return dict(track_id=ident, bbox_xyxy=[x,y,x+40,y+40], confidence=conf, missing_mask=0)
        sequences = {
            "impact": [[obj(1,100),obj(2,240-4*min(i,29))] for i in range(80)],
            "stationary_overlap": [[obj(1,100),obj(2,115)] for _ in range(80)],
            "parallel": [[obj(1,100+2*i),obj(2,115+2*i)] for i in range(80)],
            "braking_apart": [[obj(1,100),obj(2,240-4*min(i,29),200)] for i in range(80)],
            "crossing": [[obj(1,100),obj(2,240-4*i)] for i in range(70)],
            "id_switch": [[obj(1,100),obj(2 if i<29 else 20,240-4*min(i,29))] for i in range(70)],
            "weak_confidence": [[obj(1,100,conf=.2),obj(2,240-4*min(i,29),conf=.2)] for i in range(70)],
            "short_gap": [[obj(1,100)]+([] if i==32 else [obj(2,240-4*min(i,29))]) for i in range(70)],
            "scene_cut": [[obj(1,100),obj(2,240-4*min(i,29))] for i in range(70)],
        }
        for name, sequence in sequences.items():
            frames = [dict(frame_index=i,video_time_s=i/20,source_time_s=None,observations=o) for i,o in enumerate(sequence)]
            engine = CollisionRules(cfg)
            expected = [engine.update(frame,scene_cut=name=="scene_cut" and i==30) for i,frame in enumerate(frames)]
            actual = driver.execute_script("const engine=new TrafficCore.Rules(arguments[0]);return arguments[1].map((f,i)=>engine.update(f,arguments[2]&&i===30));",cfg,frames,name=="scene_cut")
            close(expected, actual)
        checks.append("javascript_v5_decisions_features_and_events_match_python_on_nine_behavior_sequences")
        detector = driver.execute_script("const a=new Float32Array(84*2);for(let i=0;i<2;i++){a[i]=320;a[2+i]=320;a[4+i]=100;a[6+i]=100;a[12+i]=.9-i*.1;}return TrafficCore.decode(a,[1,84,2],1280,720);")
        assert len(detector) == 1 and detector[0]["class_name"] == "car"
        close(detector[0]["bbox_xyxy"], [540,260,740,460])
        track = driver.execute_script("const t=new TrafficCore.Tracker(),o=x=>[{bbox_xyxy:[x,0,x+40,40],confidence:.8,class_name:'car'}];return [t.update(o(0),0)[0].track_id,t.update(o(4),1)[0].track_id,t.update(o(8),6)[0].track_id];")
        assert track == [1,1,2]
        checks.append("nms_letterbox_coordinates_and_tracker_gap_identity")
        driver.execute_script("window.__requests=[];const f=window.fetch.bind(window);window.fetch=(url,opts)=>{window.__requests.push({url:String(url),method:opts?.method||'GET',bodyType:opts?.body?.constructor?.name||null});return f(url,opts)};window.__report=null;const c=URL.createObjectURL.bind(URL);URL.createObjectURL=blob=>{if(blob.type==='application/json')blob.text().then(t=>window.__report=JSON.parse(t));return c(blob)};")
        bad = output / "invalid.mp4"
        bad.write_text("not a video")
        get("file").send_keys(str(bad))
        wait.until(lambda d: get("upload-error").is_displayed())
        assert not get("analyze").is_enabled()
        checks.append("invalid_video_is_rejected_and_analysis_stays_disabled")
        get("file").send_keys(str((ROOT / args.video).resolve()))
        wait.until(lambda d: get("analyze").is_enabled())
        get("analyze").click()
        start = time.monotonic()
        while not get("download-json").is_enabled():
            if get("upload-error").is_displayed():
                raise AssertionError(get("upload-error").text)
            if time.monotonic()-start > 600: raise TimeoutError(get("status").text)
            time.sleep(2)
            if int(time.monotonic()-start) % 20 < 2: print(get("status").text, flush=True)
        get("download-json").click()
        wait.until(lambda d: d.execute_script("return window.__report!==null"))
        report = driver.execute_script("return window.__report")
        assert report["complete"] and report["processed_samples"] == math.ceil(report["file"]["duration_s"]*20)
        assert report["file"]["sha256"] == hashlib.sha256((ROOT / args.video).read_bytes()).hexdigest()
        assert len(report["frames"]) == report["processed_samples"]
        assert sum(len(f["observations"]) for f in report["frames"]) > 0
        assert all(f["frame_index"]==i and abs(f["decoded_video_time_s"]-i/20)<.002 for i,f in enumerate(report["frames"]))
        assert report["method"]["tracker"] == "browser_iou_velocity_v1"
        assert report["independent_accuracy_evaluated"] is False
        assert report["method"]["model"]["source_weights_sha256"] == "f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36"
        (output / "actual_upload_report.json").write_text(json.dumps(report,ensure_ascii=False)+"\n")
        checks.append("real_uploaded_video_full_duration_onnx_wasm_inference_fingerprint_and_json_export")
        driver.execute_script("document.getElementById('input-video').currentTime=5.5")
        wait.until(lambda d: "5.50s" in get("frame-info").text)
        assert get("download-image").is_enabled()
        driver.get_full_page_screenshot_as_file(str(output / "upload_result.png"))
        checks.append("replay_seeks_to_analyzed_sample_and_snapshot_export_available")
        # Reuse model; cancellation must discard the previous completed report.
        get("analyze").click()
        wait.until(lambda d: get("cancel").is_displayed())
        get("cancel").click()
        assert not get("download-json").is_enabled() and get("analyze").is_enabled()
        assert "Đã hủy" in get("status").text
        checks.append("cancel_releases_worker_and_invalidates_stale_downloads")
        requests = driver.execute_script("return window.__requests")
        assert all(r["method"]=="GET" and r["bodyType"] is None for r in requests)
        assert not any("/api/uploads" in r["url"] for r in requests)
        driver.set_window_size(390,844)
        assert driver.execute_script("return document.documentElement.scrollWidth<=innerWidth+1")
        driver.get_full_page_screenshot_as_file(str(output / "mobile.png"))
        checks.append("no_video_upload_network_request_and_mobile_no_horizontal_overflow")
        summary = dict(passed=True,url=args.url,checks=checks,inference_executed=True,
                       processed_samples=report["processed_samples"],observations=sum(len(f["observations"]) for f in report["frames"]),
                       suspected_events=len(report["events"]),elapsed_s=report["elapsed_s"],accuracy_benchmark=False)
        (output / "browser_check.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    except Exception:
        driver.get_full_page_screenshot_as_file(str(output / "failure.png"))
        raise
    finally:
        try: driver.quit()
        except Exception as e: print("Browser cleanup:",type(e).__name__,flush=True)


if __name__ == "__main__": main()
