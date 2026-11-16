"""Optional Firefox end-to-end QA (selenium 4.38.0; not a demo dependency)."""
from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/audits/delivery_2026-11-14"


def main():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.support.ui import Select,WebDriverWait
    OUT.mkdir(parents=True,exist_ok=True)
    profiles=OUT/"webdriver-profiles";profiles.mkdir(exist_ok=True)
    os.environ["SE_CACHE_PATH"]=str(ROOT/".cache/selenium")
    options=Options();options.add_argument("-headless")
    snap_binary=Path("/snap/firefox/current/usr/lib/firefox/firefox")
    options.binary_location=str(snap_binary) if snap_binary.exists() else "/usr/bin/firefox"
    service_options={"executable_path":"/snap/bin/geckodriver"} if Path("/snap/bin/geckodriver").exists() else {}
    service=Service(**service_options,log_output=str(OUT/"webdriver.log"),service_args=["--profile-root",str(profiles)])
    driver=webdriver.Firefox(options=options,service=service)
    passed=[]
    try:
        driver.set_window_size(1500,1100);driver.get("http://127.0.0.1:8765")
        wait=WebDriverWait(driver,45)
        def element(identity):return driver.find_element(By.ID,identity)
        wait.until(lambda d:element("metric-frames").text=="221")
        wait.until(lambda d:d.execute_script("return ['original','processed'].every(id=>document.getElementById(id).readyState>=2)"))
        passed.append("initial_real_metrics_and_both_videos_decoded")
        driver.execute_script("document.getElementById('seek').value=110;document.getElementById('seek').dispatchEvent(new Event('input'))")
        wait.until(lambda d:element("current-frame").text=="110")
        wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,"#objects tr"))>0)
        element("play").click()
        wait.until(lambda d:d.execute_script("return document.getElementById('processed').currentTime>5.8"))
        element("play").click()
        times=driver.execute_script("return ['original','processed'].map(id=>document.getElementById(id).currentTime)")
        assert abs(times[0]-times[1])<.3,times
        element("next").click()
        passed.append("seek_play_pause_step_and_synchronized_video")
        Select(element("mode")).select_by_value("detection")
        wait.until(lambda d:element("video-method").text=="YOLO DETECTION" and element("metric-ids").text=="—")
        Select(element("sample")).select_by_value("detrac-mvi20011")
        wait.until(lambda d:element("metric-frames").text=="250")
        Select(element("mode")).select_by_value("tracking")
        wait.until(lambda d:element("metric-ids").text=="59")
        passed.append("sample_and_method_switch_show_correct_reports")
        Select(element("sample")).select_by_value("cadp-001407")
        wait.until(lambda d:element("metric-frames").text=="221")
        element("run").click()
        wait.until(lambda d:element("run").get_attribute("disabled"))
        WebDriverWait(driver,180).until(lambda d:"Lượt chạy mới hoàn tất" in element("job-status").text)
        wait.until(lambda d:element("metric-frames").text=="221")
        passed.append("run_button_actual_cpu_job_and_polling_complete")
        driver.execute_script("document.getElementById('seek').value=110;document.getElementById('seek').dispatchEvent(new Event('input'))")
        wait.until(lambda d:element("current-frame").text=="110")
        element("review-note").send_keys("Kiểm thử trình duyệt: lưu frame đang xem, không phải nhãn tai nạn.")
        element("save-review").click()
        wait.until(lambda d:"Kiểm thử trình duyệt" in element("reviews").text)
        assert not element("error").is_displayed(),element("error").text
        passed.append("manual_review_form_and_persistent_evidence_link")
        driver.execute_script("window.scrollTo(0,0)")
        driver.get_full_page_screenshot_as_file(str(OUT/"dashboard.png"))
        driver.find_element(By.CSS_SELECTOR,'[data-page="system"]').click()
        assert element("system").is_displayed() and not element("workspace").is_displayed()
        driver.find_element(By.CSS_SELECTOR,'[data-page="guide"]').click()
        assert element("guide").is_displayed()
        driver.find_element(By.CSS_SELECTOR,'[data-page="workspace"]').click()
        passed.append("system_and_guide_navigation")
        driver.set_window_size(390,844)
        driver.execute_script("window.scrollTo(0,0)")
        assert driver.execute_script("return document.documentElement.scrollWidth<=window.innerWidth+1")
        driver.get_full_page_screenshot_as_file(str(OUT/"dashboard_mobile.png"))
        passed.append("mobile_390px_without_horizontal_overflow")
        report=dict(checked_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),passed=True,
                    browser=driver.capabilities.get("browserName"),version=driver.capabilities.get("browserVersion"),checks=passed,
                    collision_accuracy_measured=False)
        (OUT/"browser_acceptance.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:driver.quit()


if __name__=="__main__":main()
