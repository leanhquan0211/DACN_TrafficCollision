"""Browser acceptance for the static demo, including GitHub project subpaths."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / "outputs"):
        parser.error("Evidence belongs below outputs/")
    output.mkdir(parents=True, exist_ok=True)
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.support.ui import Select, WebDriverWait
    profiles = output / "webdriver-profiles"
    profiles.mkdir(exist_ok=True)
    os.environ["SE_CACHE_PATH"] = str(ROOT / ".cache/selenium")
    options = Options()
    options.add_argument("-headless")
    binary = Path("/snap/firefox/current/usr/lib/firefox/firefox")
    options.binary_location = str(binary) if binary.exists() else "/usr/bin/firefox"
    service_args = dict(executable_path="/snap/bin/geckodriver") if Path("/snap/bin/geckodriver").exists() else {}
    service = Service(**service_args, log_output=str(output / "webdriver.log"),
                      service_args=["--profile-root", str(profiles)])
    driver = webdriver.Firefox(options=options, service=service)
    checks = []
    try:
        driver.set_window_size(1500, 1100)
        driver.get(args.url)
        wait = WebDriverWait(driver, 60)
        def element(name):
            return driver.find_element(By.ID, name)
        def decoded():
            wait.until(lambda d: d.execute_script("return ['original','processed'].every(id=>document.getElementById(id).readyState>=2)"))
        wait.until(lambda d: element("metric-frames").text == "221")
        decoded()
        assert "frame 109" in element("collision-events").text
        checks.append("initial_cadp_221_frames_actual_videos_decode_and_alert_109")
        element("jump-alert").click()
        wait.until(lambda d: element("current-frame").text == "109")
        element("play").click()
        wait.until(lambda d: d.execute_script("return document.getElementById('processed').currentTime>5.8"))
        element("play").click()
        times = driver.execute_script("return ['original','processed'].map(id=>document.getElementById(id).currentTime)")
        assert abs(times[0] - times[1]) < .3
        element("next").click()
        assert len(driver.find_elements(By.CSS_SELECTOR, "#objects tr")) > 0
        checks.append("jump_alert_play_pause_step_and_synchronized_video")
        for sample, frames in (("detrac-mvi20011", "250"), ("cadp-001407", "221")):
            Select(element("sample")).select_by_value(sample)
            for mode in ("collision", "tracking", "detection"):
                Select(element("mode")).select_by_value(mode)
                expected = {"collision":"COLLISION RULES", "tracking":"YOLO + BYTETRACK", "detection":"YOLO DETECTION"}[mode]
                wait.until(lambda d: element("metric-frames").text == frames and element("video-method").text == expected)
                decoded()
                if mode == "detection":
                    assert element("metric-ids").text == "—"
                if mode == "collision" and sample == "detrac-mvi20011":
                    assert not driver.find_elements(By.CSS_SELECTOR, "#collision-events .automatic-event")
                    assert element("jump-alert").get_attribute("disabled")
                assert not element("error").is_displayed(), element("error").text
        checks.append("both_samples_all_three_modes_correct_metrics_no_stale_alert_and_video_decode")
        Select(element("mode")).select_by_value("collision")
        wait.until(lambda d: "frame 109" in element("collision-events").text)
        decoded()
        links = driver.execute_script("return [...document.querySelectorAll('#downloads a,#collision-events a')].map(a=>a.href)")
        assert len(links) == 6
        assert not driver.find_elements(By.CSS_SELECTOR, "input[type=file]")
        requests = driver.execute_script("return performance.getEntriesByType('resource').map(r=>r.name)")
        assert not any("/api/" in url for url in requests)
        checks.append("static_only_no_backend_or_upload_requests_and_six_artifact_links")
        for page in ("system", "guide", "workspace"):
            driver.find_element(By.CSS_SELECTOR, f'[data-page="{page}"]').click()
            assert element(page).is_displayed()
        checks.append("system_guide_workspace_navigation")
        driver.find_element(By.CSS_SELECTOR, '[data-page="system"]').click()
        wait.until(lambda d: element("evaluation-results").is_displayed())
        vehicle = element("vehicle-evaluation").text
        accident = element("b0-evaluation").text
        assert all(value in vehicle for value in ("90,60%", "87,32%", "81,39%", "80,81%")), vehicle
        assert all(value in accident for value in ("83,24%", "1,21%", "25 ảnh", "18 ảnh")), accident
        assert "precision không xác định" in element("b0-fixed-result").text
        assert "chưa có precision/recall sự kiện trên test độc lập" in element("evaluation-panel").text
        assert len(driver.find_elements(By.CSS_SELECTOR, "#evaluation-results a")) == 3
        driver.get_full_page_screenshot_as_file(str(output / "evaluation.png"))
        driver.set_window_size(390, 844)
        assert driver.execute_script("return document.documentElement.scrollWidth<=window.innerWidth+1")
        driver.get_full_page_screenshot_as_file(str(output / "evaluation_mobile.png"))
        driver.set_window_size(1500, 1100)
        driver.find_element(By.CSS_SELECTOR, '[data-page="workspace"]').click()
        checks.append("evaluation_metrics_training_scope_undefined_precision_and_mobile_layout")
        element("jump-alert").click()
        wait.until(lambda d: driver.execute_script("return !document.getElementById('processed').seeking"))
        driver.get_full_page_screenshot_as_file(str(output / "dashboard.png"))
        driver.set_window_size(390, 844)
        assert driver.execute_script("return document.documentElement.scrollWidth<=window.innerWidth+1")
        driver.get_full_page_screenshot_as_file(str(output / "dashboard_mobile.png"))
        checks.append("mobile_390px_without_horizontal_overflow")
        driver.refresh()
        wait.until(lambda d: element("metric-frames").text == "221")
        assert "frame 109" in element("collision-events").text
        checks.append("refresh_initializes_under_project_subpath")
        report = dict(checked_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(), passed=True,
                      url=args.url, browser=driver.capabilities.get("browserName"), checks=checks,
                      links=links, inference_executed_in_browser=False)
        (output / "browser_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    finally:
        try:
            driver.quit()
        except Exception as exc:
            print(f"Browser cleanup: {type(exc).__name__}", flush=True)


if __name__ == "__main__":
    main()
