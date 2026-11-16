"use strict";
const $ = id => document.getElementById(id);
const original = $("original"), processed = $("processed");
const names = {car:"Ô tô",bus:"Xe buýt",truck:"Xe tải",bicycle:"Xe đạp",motorcycle:"Xe máy",motorbike:"Xe máy"};
const modes = {collision:"COLLISION RULES",tracking:"YOLO + BYTETRACK",detection:"YOLO DETECTION"};
const number = n => Number(n).toLocaleString("vi-VN");
let catalog, current, frameIndex = 0, generation = 0;
function error(message) { $("error").textContent = message; $("error").hidden = !message; }
async function readJSON(path) {
  const response = await fetch(new URL(path, document.baseURI));
  if (!response.ok) throw new Error(`Không tải được kết quả (HTTP ${response.status}). Thử tải lại trang.`);
  return response.json();
}
function pause() { original.pause(); processed.pause(); $("play").textContent = "▶ Phát"; }
function enablePlayback(enabled) { for (const id of ["play","previous","next","seek"]) $(id).disabled = !enabled; }
function drawChart() {
  const canvas = $("chart"), width = canvas.clientWidth - 36;
  if (width < 1) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio; canvas.height = 54 * ratio;
  const ctx = canvas.getContext("2d"); ctx.scale(ratio,ratio);
  if (!current) return;
  const counts = current.counts, maximum = Math.max(1,...counts);
  ctx.beginPath(); counts.forEach((n,i) => {
    const x = i / Math.max(1,counts.length-1) * width, y = 48 - n / maximum * 37;
    i ? ctx.lineTo(x,y) : ctx.moveTo(x,y);
  }); ctx.strokeStyle = "#5ee0bb"; ctx.lineWidth = 1.4; ctx.stroke();
  for (const [index,color] of [[frameIndex,"#f1cd8d"],...(current.events || []).map(e => [e.frame_index,"#ff7373"])]) {
    const x = index / Math.max(1,counts.length-1) * width;
    ctx.strokeStyle = color; ctx.beginPath(); ctx.moveTo(x,1); ctx.lineTo(x,53); ctx.stroke();
  }
}
function renderFrame(index) {
  if (!current) return;
  frameIndex = Math.max(0,Math.min(current.frames.length-1,index));
  const frame = current.frames[frameIndex];
  $("seek").value = frameIndex; $("frame-label").textContent = `Frame ${frameIndex} / ${current.frames.length-1}`;
  $("current-frame").textContent = frameIndex; $("objects-count").textContent = `${frame.observations.length} quan sát`;
  const rows = frame.observations.map(o => {
    const tr = document.createElement("tr");
    const values = [o.track_id === null ? "—" : `#${o.track_id}`, names[o.class_name] || o.class_name, `${(o.confidence*100).toFixed(1)}%`, o.track_id === null ? "—" : o.track_age_observations];
    values.forEach((value,i) => { const td = document.createElement("td"); td.textContent = value; if (!i) td.className = "track"; tr.append(td); });
    return tr;
  });
  if (!rows.length) { const tr = document.createElement("tr"), td = document.createElement("td"); td.colSpan = 4; td.textContent = "Không có quan sát tại frame này."; tr.append(td); rows.push(tr); }
  $("objects").replaceChildren(...rows); drawChart();
}
function seek(index) {
  if (!current) return;
  pause(); index = Math.max(0,Math.min(current.frames.length-1,index));
  for (const video of [original,processed]) video.currentTime = index / current.report.container_fps;
  renderFrame(index);
}
function link(path,text) {
  const a = document.createElement("a"); a.href = path; a.textContent = text;
  a.target = "_blank"; a.rel = "noopener"; return a;
}
function renderEvents() {
  const collision = current.report.mode === "collision", events = current.events || [];
  $("automatic-alerts").hidden = !collision; $("collision-events").replaceChildren();
  $("jump-alert").disabled = !collision || !events.length;
  $("jump-alert").textContent = collision && !events.length ? "Không có mốc cảnh báo" : "↗ Xem mốc cảnh báo";
  $("collision-state").textContent = events.length ? `Có ${events.length} cảnh báo nghi va chạm trong lượt chạy đã lưu.` : "Luật chưa phát cảnh báo trên clip này.";
  for (const event of events) {
    const card = document.createElement("div"); card.className = "automatic-event";
    const title = document.createElement("strong"); title.textContent = `${event.event_id} · NGHI VA CHẠM · frame ${event.frame_index}`;
    const note = document.createElement("p"); note.textContent = `ID ${event.track_ids.join(" + ")} · thời gian video ${event.video_time_s.toFixed(2)}s · cần người xem kiểm tra`;
    const button = document.createElement("button"); button.className = "small-button"; button.textContent = "Xem thời điểm cảnh báo"; button.onclick = () => seek(event.frame_index);
    card.append(title,note,button,link(event.snapshot_url,"Ảnh bằng chứng ↗"),link(event.clip_url,"Clip bằng chứng ↗"));
    $("collision-events").append(card);
  }
}
async function loadSelected() {
  const version = ++generation; pause(); error(""); current = null; enablePlayback(false);
  $("jump-alert").disabled = true; $("automatic-alerts").hidden = true; $("collision-events").replaceChildren();
  $("run-state").textContent = "Đang tải kết quả…"; $("objects").replaceChildren(); $("downloads").replaceChildren();
  for (const id of ["metric-frames","metric-obs","metric-ids","metric-fps"]) $(id).textContent = "—";
  for (const video of [original,processed]) { video.removeAttribute("src"); video.load(); }
  const sample = catalog.samples.find(s => s.id === $("sample").value), mode = $("mode").value;
  $("sample-description").textContent = sample.description;
  try {
    const run = await readJSON(sample.runs[mode]); if (version !== generation) return;
    if (!run.frames.length || run.frames.length !== run.report.processed_frames) throw new Error("Dữ liệu frame không khớp lượt chạy.");
    current = run; const report = run.report;
    $("metric-frames").textContent = number(report.processed_frames); $("metric-obs").textContent = number(report.observation_count);
    $("metric-ids").textContent = mode === "detection" ? "—" : number(report.unique_track_ids);
    $("metric-fps").textContent = report.runtime.offline_processing_fps.toFixed(2);
    $("video-method").textContent = modes[mode]; $("run-state").textContent = "✓ Kết quả đã kiểm trước khi xuất bản";
    $("seek").max = report.processed_frames-1;
    $("time-note").textContent = report.source_seconds_verified ? "Thời gian nguồn đã đối chiếu" : "Giây video · chưa xác minh thời gian nguồn";
    const quality = report.collision_quality;
    $("quality-note").textContent = quality ? `${quality.frames_with_two_eligible_tracks}/${report.processed_frames} frame có ít nhất hai xe đủ điều kiện qua bước lọc chất lượng; xe quá nhỏ/xa có thể bị bỏ qua.` : "Chế độ này chỉ phát hiện/theo dõi phương tiện, chưa xác minh sự kiện va chạm.";
    $("provenance").textContent = `CPU · lượt chạy ${report.checked_at.slice(0,10)} · SHA-256 report gốc ${run.original_report_sha256.slice(0,16)}… · FPS offline, chưa là benchmark streaming.`;
    const titles = {output:"MP4 kết quả ↓",cache:"Cache JSONL ↓",report:"Tóm tắt JSON ↓",events:"Events JSON ↓"};
    $("downloads").replaceChildren(...Object.entries(titles).filter(([kind]) => run.assets[kind]).map(([kind,text]) => { const a = link(run.assets[kind],text); a.download = ""; return a; }));
    original.src = run.assets.source; processed.src = run.assets.output;
    for (const video of [original,processed]) { video.playbackRate = Number($("speed").value); video.load(); }
    renderEvents(); renderFrame(0); enablePlayback(true);
  } catch (e) { if (version === generation) { current = null; enablePlayback(false); $("run-state").textContent = "Chưa tải được kết quả"; error(e.message); } }
}
$("play").onclick = async () => {
  if (!current) return;
  if (!processed.paused) { pause(); return; }
  try { if (processed.ended) seek(0); original.currentTime = processed.currentTime; await Promise.all([original.play(),processed.play()]); $("play").textContent = "Ⅱ Dừng"; }
  catch (e) { pause(); error("Chưa phát được video. Thử bấm phát lại hoặc tải MP4 kết quả. " + e.message); }
};
processed.addEventListener("timeupdate",() => {
  if (!current) return;
  if (!processed.paused && Math.abs(original.currentTime-processed.currentTime) > .15) original.currentTime = processed.currentTime;
  const index = Math.min(current.frames.length-1,Math.floor(processed.currentTime*current.report.container_fps+1e-5));
  if (index !== frameIndex) renderFrame(index);
});
processed.addEventListener("ended",pause);
for (const video of [original,processed]) video.addEventListener("error",() => { if (video.getAttribute("src")) error("Không tải được MP4. Kiểm tra kết nối hoặc tải video kết quả để xem."); });
$("seek").oninput = () => seek(Number($("seek").value)); $("previous").onclick = () => seek(frameIndex-1); $("next").onclick = () => seek(frameIndex+1);
$("speed").onchange = () => { for (const video of [original,processed]) video.playbackRate = Number($("speed").value); };
$("jump-alert").onclick = () => { if (current?.events.length) seek(current.events[0].frame_index); };
$("sample").onchange = loadSelected; $("mode").onchange = loadSelected;
document.querySelectorAll("[data-page]").forEach(button => button.onclick = () => {
  pause(); document.querySelectorAll("[data-page]").forEach(b => b.classList.toggle("active",b === button));
  document.querySelectorAll(".page").forEach(page => page.hidden = page.id !== button.dataset.page); drawChart();
});
window.addEventListener("resize",drawChart);
(async () => {
  try {
    catalog = await readJSON("./data/catalog.json");
    $("sample").replaceChildren(...catalog.samples.map(sample => { const option = document.createElement("option"); option.value = sample.id; option.textContent = sample.title; return option; }));
    $("sample").disabled = false; $("mode").disabled = false; await loadSelected();
  } catch (e) { error(e.message); }
})();
