"use strict";
const $ = id => document.getElementById(id);
let catalog, current, frameIndex = 0, generation = 0, frameRequest = 0, jobId = null;
let lastRendered = -1, jobBusy = false, polling = false, uploading = false;
const original = $("original"), processed = $("processed");
const classNames = {car:"Ô tô",bus:"Xe buýt",truck:"Xe tải",bicycle:"Xe đạp",motorcycle:"Xe máy",motorbike:"Xe máy"};
const number = n => n.toLocaleString("vi-VN");
function error(message) { $("error").textContent = message; $("error").hidden = !message; }
async function api(path, data) {
  const options = data ? {method:"POST",headers:{"Content-Type":"application/json","X-Demo-Token":catalog.token},body:JSON.stringify(data)} : {};
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  return result;
}
function selectedSample(){ return catalog.samples.find(s => s.id === $("sample").value); }
function setBusy(busy) {jobBusy=busy; $("run").disabled=busy || uploading || !selectedSample()?.available;$("upload-button").disabled=busy || uploading;$("upload-file").disabled=uploading;}
async function refreshCatalog(){
  const previous = $("sample").value;
  catalog = await api("/api/catalog");
  $("sample").replaceChildren(...catalog.samples.map(s=>{const option=document.createElement("option");option.value=s.id;option.textContent=s.title+(s.available?"":" · thiếu file");return option;}));
  if(catalog.samples.some(s=>s.id===previous)) $("sample").value=previous;
  $("asset-status").replaceChildren();
  for(const item of catalog.samples){const p=document.createElement("p");p.textContent=`${item.title}: ${Object.keys(item.runs).length}/3 chế độ đã kiểm${item.available?"":" · thiếu video đầu vào"}`;$("asset-status").append(p);}
  for(const message of catalog.errors){const p=document.createElement("p");p.textContent=message;$("asset-status").append(p);}
}
function pause(){processed.pause();original.pause();$("play").textContent="▶ Phát";}
function clearRun(){pause();current=null;lastRendered=-1;$("automatic-alerts").hidden=true;$("collision-events").replaceChildren();$("run-state").textContent="Chưa có kết quả đã kiểm";for(const v of [original,processed]){v.removeAttribute("src");v.load();}for(const id of ["metric-frames","metric-obs","metric-ids","metric-fps"])$(id).textContent="—";$("objects").replaceChildren();$("reviews").replaceChildren();$("downloads").replaceChildren();$("save-review").disabled=true;$("provenance").textContent="Chạy pipeline để tạo kết quả.";drawChart();}
function renderEvents(){
  $("automatic-alerts").hidden=current.report.mode!=="collision";$("collision-events").replaceChildren();
  if(current.report.mode!=="collision")return;
  const events=current.events||[];$("collision-state").textContent=events.length?`Có ${events.length} cảnh báo nghi va chạm do hệ thống tạo. Chọn sự kiện để xem bằng chứng.`:"Luật chưa phát cảnh báo trên video này.";
  const quality=current.report.collision_quality;if(quality)$("collision-state").textContent+=` Có ${quality.frames_with_two_eligible_tracks}/${current.report.processed_frames} frame đủ ít nhất hai xe qua bước lọc chất lượng. Xe quá nhỏ/xa có thể không được phân tích.`;
  for(const event of events){const card=document.createElement("div");card.className="automatic-event";
    const title=document.createElement("strong");title.textContent=`${event.event_id} · NGHI VA CHẠM · frame ${event.frame_index}`;
    const note=document.createElement("p");note.textContent=`ID ${event.track_ids.join(" + ")} · thời gian video ${event.video_time_s.toFixed(2)}s · 4 tín hiệu và xác nhận nhiều frame`;
    const jump=document.createElement("button");jump.className="small-button";jump.textContent="Xem thời điểm cảnh báo";jump.onclick=()=>seek(event.frame_index);
    const links=[['snapshot','Ảnh bằng chứng ↗'],['clip','Clip bằng chứng ↗']].map(([kind,text])=>{const a=document.createElement("a");a.href=`/collision-evidence?run=${current.id}&event=${event.event_id}&kind=${kind}`;a.target="_blank";a.textContent=text;return a;});
    card.append(title,note,jump,...links);$("collision-events").append(card);
  }
}
async function loadSelected(){
  const version=++generation; ++frameRequest; error(""); clearRun();
  const sample=selectedSample();const mode=$("mode").value;
  $("sample-description").textContent=sample.description;setBusy(jobBusy);
  const id=sample.runs[mode];
  if(!id){$("provenance").textContent="Video đã sẵn sàng. Bấm Chạy lại trên CPU để phân tích.";return;}
  try{
    const run=await api(`/api/run?id=${id}`);if(version!==generation)return;
    current=run;const report=run.report;
    $("metric-frames").textContent=number(report.processed_frames);
    $("metric-obs").textContent=number(report.observation_count);
    $("metric-ids").textContent=mode!=="detection"?number(report.unique_track_ids):"—";
    $("metric-fps").textContent=report.runtime.offline_processing_fps.toFixed(1)+" fps";
    $("run-state").textContent=report.current_collision_config===false?"Kết quả dùng luật cũ · Chạy lại trên CPU để cập nhật":"● Đã kiểm MP4 · cache · hash";
    $("video-method").textContent=mode==="collision"?"PHÁT HIỆN VA CHẠM · THỬ NGHIỆM":(mode==="tracking"?"YOLO + BYTETRACK":"YOLO DETECTION");
    $("seek").max=report.processed_frames-1;$("seek").value=0;frameIndex=0;
    original.src=`/media?id=${id}&kind=source`;processed.src=`/media?id=${id}&kind=output`;
    for(const v of [original,processed])v.playbackRate=Number($("speed").value);
    $("time-note").textContent=report.source_seconds_verified?"Thời gian nguồn đã có evidence":"Timeline theo video; chưa chứng nhận giây nguồn";
    $("provenance").textContent=`${report.device.toUpperCase()} · ${report.cpu_threads} threads · ${new Date(report.checked_at).toLocaleString("vi-VN")} · input SHA256 ${report.input_sha256.slice(0,16)}…`;
    const links=[["output","↓ MP4"],["cache","↓ JSONL"],["report","↓ Report"]];
    if(mode==="collision")links.push(["events","↓ Events JSON"]);
    $("downloads").replaceChildren(...links.map(([kind,text])=>{const a=document.createElement("a");a.href=`/download?id=${id}&kind=${kind}`;a.textContent=text;return a;}));
    const reviews=document.createElement("a");reviews.href=`/download-reviews?id=${id}`;reviews.target="_blank";reviews.textContent="↗ Review JSON";$("downloads").append(reviews);
    $("save-review").disabled=false;renderEvents();await renderFrame(0);await loadReviews();drawChart();
  }catch(e){if(version===generation)error(e.message);}
}
async function renderFrame(index){
  if(!current)return; const id=current.id;
  frameIndex=Math.max(0,Math.min(index,current.report.processed_frames-1));
  $("seek").value=frameIndex;$("frame-label").textContent=`Frame ${frameIndex} / ${current.report.processed_frames-1}`;
  $("current-frame").textContent=frameIndex;drawChart();
  if(lastRendered===frameIndex)return;lastRendered=frameIndex;
  const request=++frameRequest;
  try{
    const frame=await api(`/api/frame?id=${id}&index=${frameIndex}`);
    if(request!==frameRequest || !current || current.id!==id)return;
    $("objects-count").textContent=`${frame.observations.length} bbox · ${frame.missing_tracks.length} ID thiếu`;
    const rows=frame.observations.map(o=>{const tr=document.createElement("tr");const values=[o.track_id===null?"—":`#${o.track_id}`,classNames[o.class_name]||o.class_name,`${(o.confidence*100).toFixed(1)}%`,o.track_id===null?"—":o.track_age_observations];values.forEach((v,i)=>{const td=document.createElement("td");td.textContent=v;if(i===0)td.className="track";tr.append(td);});return tr;});
    if(!rows.length){const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=4;td.textContent="Không có quan sát tại frame này.";tr.append(td);rows.push(tr);}
    $("objects").replaceChildren(...rows);
  }catch(e){if(request===frameRequest)error(e.message);}
}
function seek(index){if(!current)return;pause();const max=current.report.processed_frames-1;index=Math.max(0,Math.min(max,index));const t=index/current.report.container_fps;for(const v of [original,processed])v.currentTime=t;renderFrame(index);}
function drawChart(){
  const canvas=$("chart");const width=canvas.clientWidth-36; if(width<1)return;
  const ratio=window.devicePixelRatio||1;canvas.width=width*ratio;canvas.height=54*ratio;
  const ctx=canvas.getContext("2d");ctx.scale(ratio,ratio);ctx.clearRect(0,0,width,54);
  if(!current)return;const counts=current.counts;const max=Math.max(1,...counts);
  ctx.beginPath();ctx.moveTo(0,50);counts.forEach((n,i)=>ctx.lineTo(i/Math.max(1,counts.length-1)*width,48-n/max*37));ctx.lineTo(width,50);ctx.closePath();ctx.fillStyle="rgba(94,224,187,.10)";ctx.fill();
  ctx.beginPath();counts.forEach((n,i)=>{const x=i/Math.max(1,counts.length-1)*width,y=48-n/max*37;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.strokeStyle="#5ee0bb";ctx.lineWidth=1.4;ctx.stroke();
  const x=frameIndex/Math.max(1,counts.length-1)*width;ctx.strokeStyle="#f1cd8d";ctx.beginPath();ctx.moveTo(x,4);ctx.lineTo(x,53);ctx.stroke();
  ctx.strokeStyle="#ff7373";for(const event of current.events||[]){const marker=event.frame_index/Math.max(1,counts.length-1)*width;ctx.beginPath();ctx.moveTo(marker,0);ctx.lineTo(marker,54);ctx.stroke();}
}
async function loadReviews(){
  if(!current)return;const id=current.id;const reviews=await api(`/api/reviews?id=${id}`);if(!current||current.id!==id)return;
  $("reviews").replaceChildren(...reviews.slice().reverse().map(r=>{const div=document.createElement("div");div.className="review-item";const small=document.createElement("small");small.textContent=`FRAME ${r.frame_index} · NHẬN XÉT THỦ CÔNG`;const p=document.createElement("p");p.textContent=r.note;const a=document.createElement("a");a.textContent="Mở ảnh gốc ↗";a.target="_blank";a.href=`/evidence?run=${id}&review=${r.id}`;const jump=document.createElement("button");jump.textContent="Tới frame";jump.className="small-button";jump.style.marginLeft="12px";jump.onclick=()=>seek(r.frame_index);div.append(small,p,a,jump);return div;}));
}
$("review-form").addEventListener("submit",async event=>{event.preventDefault();if(!current)return;pause();const button=$("save-review");button.disabled=true;try{await api("/api/reviews",{run_id:current.id,frame_index:frameIndex,note:$("review-note").value});$("review-note").value="";await loadReviews();error("");}catch(e){error(e.message);}finally{button.disabled=!current;}});
$("play").onclick=async()=>{if(!current)return;if(!processed.paused){pause();return;}try{if(processed.ended)seek(0);original.currentTime=processed.currentTime;await Promise.all([original.play(),processed.play()]);$("play").textContent="Ⅱ Dừng";}catch(e){pause();error("Không phát được video: "+e.message);}};
processed.addEventListener("timeupdate",()=>{if(!current)return;if(!processed.paused&&Math.abs(original.currentTime-processed.currentTime)>.15)original.currentTime=processed.currentTime;const index=Math.min(current.report.processed_frames-1,Math.floor(processed.currentTime*current.report.container_fps+1e-5));if(index!==frameIndex)renderFrame(index);});
processed.addEventListener("ended",pause);
for(const v of [original,processed])v.addEventListener("error",()=>{if(v.getAttribute("src"))error("Trình duyệt không đọc được MP4. Thử Firefox/Chrome hoặc tải MP4 để mở bằng trình phát.");});
$("seek").oninput=()=>seek(Number($("seek").value));$("previous").onclick=()=>seek(frameIndex-1);$("next").onclick=()=>seek(frameIndex+1);
$("speed").onchange=()=>{for(const v of [original,processed])v.playbackRate=Number($("speed").value);};
$("sample").onchange=loadSelected;$("mode").onchange=loadSelected;
$("run").onclick=async()=>{try{error("");pause();const job=await api("/api/jobs",{sample_id:selectedSample().id,mode:$("mode").value});jobId=job.id;setBusy(true);$("job-status").textContent="Đang chạy YOLO trên CPU… Kết quả mới sẽ được kiểm trước khi hiển thị.";}catch(e){error(e.message);}};
$("upload-form").addEventListener("submit",async event=>{
  event.preventDefault();const file=$("upload-file").files[0];if(!file)return;
  if(!file.name.toLowerCase().endsWith(".mp4") || !file.size || file.size>catalog.max_upload_bytes){error("Chọn MP4 H.264 không rỗng, tối đa 100 MiB.");return;}
  uploading=true;setBusy(jobBusy);pause();error("");$("job-status").textContent="Đang tải và kiểm tra video…";
  try{
    const response=await fetch("/api/uploads",{method:"POST",headers:{"X-Demo-Token":catalog.token,"X-File-Name":encodeURIComponent(file.name),"Content-Type":"application/octet-stream"},body:file});
    const result=await response.json();if(!response.ok)throw new Error(result.error||`HTTP ${response.status}`);
    await refreshCatalog();$("sample").value=result.sample_id;await loadSelected();
    const job=await api("/api/jobs",{sample_id:result.sample_id,mode:$("mode").value});jobId=job.id;setBusy(true);
    $("job-status").textContent="Video mới đang được phân tích trên CPU…";$("upload-file").value="";
  }catch(e){$("job-status").textContent="";error(e.message);}
  finally{uploading=false;setBusy(jobBusy);}
});
async function pollJob(){
  if(polling)return;polling=true;
  try{const {job}=await api("/api/job");if(!job)return;const busy=["running","validating"].includes(job.status);setBusy(busy);
    if(busy){jobId=job.id;const seconds=Math.max(0,Math.floor((Date.now()-Date.parse(job.started_at))/1000));$("job-status").textContent=`${job.status==="validating"?"Đang kiểm hash, cache và MP4":"Đang xử lý CPU"} · ${seconds} giây · Bạn vẫn có thể xem kết quả cũ.`;}
    else if(jobId===job.id){jobId=null;if(job.status==="complete"){await refreshCatalog();if(selectedSample().id===job.sample_id&&$("mode").value===job.mode)await loadSelected();$("job-status").textContent="✓ Lượt chạy mới hoàn tất và đã kiểm. MP4, cache và report được lưu riêng.";}else{$("job-status").textContent="Lượt chạy chưa hoàn tất.";error(job.error);}}
  }catch(e){error("Mất kết nối máy chủ. Kiểm tra terminal chạy demo. "+e.message);}finally{polling=false;}
}
document.querySelectorAll("[data-page]").forEach(button=>button.onclick=()=>{pause();document.querySelectorAll("[data-page]").forEach(b=>b.classList.toggle("active",b===button));document.querySelectorAll(".page").forEach(p=>p.hidden=p.id!==button.dataset.page);drawChart();});
window.addEventListener("resize",drawChart);
(async()=>{try{await refreshCatalog();await loadSelected();await pollJob();setInterval(pollJob,1500);}catch(e){error("Không khởi tạo được demo: "+e.message);}})();
