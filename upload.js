"use strict";
(() => {
  const $=id=>document.getElementById(id),video=$("input-video"),canvas=$("result-canvas"),ctx=canvas.getContext("2d");
  const prep=document.createElement("canvas");prep.width=prep.height=640;const pc=prep.getContext("2d",{willReadFrequently:true});
  const cutCanvas=document.createElement("canvas");cutCanvas.width=32;cutCanvas.height=18;const cc=cutCanvas.getContext("2d",{willReadFrequently:true});
  const names={car:"Ô tô",bus:"Xe buýt",truck:"Xe tải",bicycle:"Xe đạp",motorcycle:"Xe máy"};
  let worker=null,pending=null,busy=false,token=0,sourceURL=null,result=null,ready=false;
  const failure=message=>{$("upload-error").textContent=message;$("upload-error").hidden=!message;$("upload-error").style.cssText="color:#ffb7b7;overflow-wrap:anywhere";};
  function controls(){ $("file").disabled=busy;$("analysis-mode").disabled=busy;$("analyze").disabled=busy||!ready;$("cancel").hidden=!busy;video.controls=!busy; }
  function invalidate(){result=null;$("summary").textContent="Chưa có kết quả cho video này.";$("events").replaceChildren();$("download-json").disabled=$("download-image").disabled=true;$("frame-info").textContent="Chưa có kết quả";$("progress").value=0;ctx.clearRect(0,0,canvas.width,canvas.height);}
  function terminate(reason){if(worker)worker.terminate();worker=null;if(pending){pending.reject(new Error(reason));pending=null;}}
  function call(message,transfer=[]){return new Promise((resolve,reject)=>{if(pending){reject(new Error("Đang xử lý một yêu cầu khác."));return;}const timer=setTimeout(()=>{terminate("Thiết bị không phản hồi sau 180 giây. Thử clip ngắn hơn hoặc trình duyệt khác.");},180000);pending={resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}};worker.postMessage(message,transfer);});}
  async function initialize(){
    if(worker)return worker.metadata;
    worker=new Worker(new URL("./browser-worker.js",document.baseURI));
    const active=worker;
    worker.onmessage=({data})=>{
      if(worker!==active)return;
      if(data.kind==="model-progress"){$("status").textContent=`Đang tải mô hình: ${(data.loaded/1048576).toFixed(1)} / ${(data.total/1048576).toFixed(1)} MB…`;return;}
      if(data.kind==="ready")worker.metadata=data.metadata;
      const p=pending;pending=null;if(p){data.kind==="error"?p.reject(new Error(data.message)):p.resolve(data);}
    };
    worker.onerror=e=>{if(worker!==active)return;const p=pending;pending=null;if(p)p.reject(new Error(e.message||"Không khởi động được mô hình trên thiết bị này."));};
    return (await call({kind:"init"})).metadata;
  }
  function waitEvent(target,event,action){return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>finish(new Error("Không đọc được hình từ video. Thử MP4 H.264 khác.")),15000);
    const done=()=>finish(),bad=()=>finish(new Error("Trình duyệt không giải mã được video này. Thử MP4 H.264."));
    function finish(error){clearTimeout(timer);target.removeEventListener(event,done);target.removeEventListener("error",bad);error?reject(error):resolve();}
    target.addEventListener(event,done,{once:true});target.addEventListener("error",bad,{once:true});action();
  });}
  async function seek(time){if(Math.abs(video.currentTime-time)<1e-6&&video.readyState>=2)return;await waitEvent(video,"seeked",()=>{video.currentTime=time;});}
  function draw(frame){
    if(video.readyState<2)return;ctx.drawImage(video,0,0,canvas.width,canvas.height);if(!frame)return;
    const sx=canvas.width/video.videoWidth,sy=canvas.height/video.videoHeight;
    ctx.lineWidth=2;ctx.font=`${Math.max(13,canvas.width/65)}px sans-serif`;
    for(const o of frame.observations){const [x,y,x2,y2]=o.bbox_xyxy,label=`${o.track_id==null?"":`#${o.track_id} `}${names[o.class_name]||o.class_name} ${o.confidence.toFixed(2)}`;
      ctx.strokeStyle="#5ee0bb";ctx.strokeRect(x*sx,y*sy,(x2-x)*sx,(y2-y)*sy);const w=ctx.measureText(label).width+8,ty=Math.max(18,y*sy);ctx.fillStyle="#0b1220";ctx.fillRect(x*sx,ty-18,w,20);ctx.fillStyle="#eafff9";ctx.fillText(label,x*sx+4,ty-3);
    }
    for(const event of (result?.events||[]).filter(e=>Math.abs(e.video_time_s-frame.video_time_s)<.5)){
      const [x,y,x2,y2]=event.bbox_xyxy;ctx.lineWidth=4;ctx.strokeStyle="#ff7373";ctx.strokeRect(x*sx,y*sy,(x2-x)*sx,(y2-y)*sy);ctx.fillStyle="#ff7373";ctx.fillText("NGHI VA CHẠM · CẦN KIỂM TRA",12,28);
    }
    $("frame-info").textContent=`Mẫu ${frame.frame_index+1} · ${frame.video_time_s.toFixed(2)}s · ${frame.observations.length} quan sát`;
  }
  function repaint(){if(busy)return;const frame=result?.frames[Math.min(result.frames.length-1,Math.floor(video.currentTime*20+1e-5))];draw(frame);}
  for(const e of ["seeked","timeupdate","loadeddata"])video.addEventListener(e,repaint);
  if(video.requestVideoFrameCallback){const tick=()=>{if(!video.paused)repaint();video.requestVideoFrameCallback(tick);};video.requestVideoFrameCallback(tick);}
  $("file").addEventListener("change",async()=>{
    const generation=++token;video.pause();ready=false;invalidate();failure("");controls();
    if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=null;video.removeAttribute("src");video.load();
    const file=$("file").files[0];if(!file){$("status").textContent="Chọn video để bắt đầu.";return;}
    try{
      if(!/\.mp4$/i.test(file.name)||file.size===0||file.size>100*1024*1024)throw new Error("Chọn MP4 không rỗng, tối đa 100 MiB.");
      sourceURL=URL.createObjectURL(file);await waitEvent(video,"loadeddata",()=>{video.src=sourceURL;video.load();});
      if(generation!==token)return;
      if(!Number.isFinite(video.duration)||video.duration<=0||video.duration>120)throw new Error("Video cần dài hơn 0 và không quá 120 giây.");
      if(Math.max(video.videoWidth,video.videoHeight)>1920||video.videoWidth*video.videoHeight>1920*1080)throw new Error("Video quá lớn. Chọn bản Full HD hoặc thấp hơn.");
      canvas.width=Math.min(1280,video.videoWidth);canvas.height=Math.round(canvas.width*video.videoHeight/video.videoWidth);canvas.style.aspectRatio=`${video.videoWidth}/${video.videoHeight}`;
      ready=true;$("status").textContent=`Đã chọn ${file.name} · ${video.duration.toFixed(2)}s · ${video.videoWidth}×${video.videoHeight}. Bấm Phân tích video.`;draw();
    }catch(e){if(generation===token){failure(e.message);$("status").textContent="Chưa đọc được video.";}}
    finally{if(generation===token)controls();}
  });
  $("cancel").onclick=()=>{token++;terminate("Đã hủy xử lý.");busy=false;invalidate();video.pause();$("status").textContent="Đã hủy. Bạn có thể chọn video hoặc chạy lại.";controls();};
  $("upload-form").addEventListener("submit",async e=>{
    e.preventDefault();if(!ready||busy)return;const generation=++token;busy=true;controls();invalidate();failure("");video.pause();const file=$("file").files[0],mode=$("analysis-mode").value;
    try{
      $("status").textContent="Đang khởi động mô hình trên thiết bị…";
      const metadata=await initialize();if(generation!==token)return;
      const response=await fetch("./data/browser-config.json");if(!response.ok)throw new Error("Không tải được cấu hình phân tích.");const config=await response.json();
      const tracker=new TrafficCore.Tracker(),rules=new TrafficCore.Rules(config.rules,video.videoWidth,video.videoHeight),frames=[],events=[];
      const total=Math.ceil(video.duration*20),started=performance.now();let lastPixels=null;
      for(let index=0;index<total;index++){
        if(generation!==token)return;const time=index/20;await seek(time);if(generation!==token)return;
        cc.drawImage(video,0,0,32,18);const cutPixels=cc.getImageData(0,0,32,18).data;let diff=0;
        if(lastPixels)for(let i=0;i<cutPixels.length;i+=4)for(let c=0;c<3;c++)diff+=Math.abs(cutPixels[i+c]-lastPixels[i+c]);
        const cut=!!lastPixels&&diff/(32*18*3*255)>.3;lastPixels=new Uint8ClampedArray(cutPixels);if(cut)tracker.reset();
        const scale=Math.min(640/video.videoWidth,640/video.videoHeight),w=Math.round(video.videoWidth*scale),h=Math.round(video.videoHeight*scale),x=Math.round((640-w)/2-.1),y=Math.round((640-h)/2-.1);
        pc.fillStyle="rgb(114,114,114)";pc.fillRect(0,0,640,640);pc.drawImage(video,x,y,w,h);const pixels=pc.getImageData(0,0,640,640).data;
        const reply=await call({kind:"infer",id:index,pixels:pixels.buffer,width:video.videoWidth,height:video.videoHeight},[pixels.buffer]);if(generation!==token)return;
        const observations=mode==="detection"?reply.observations:tracker.update(reply.observations,index);
        const frame={frame_index:index,video_time_s:time,decoded_video_time_s:video.currentTime,source_time_s:null,scene_cut:cut,observations};
        if(mode==="collision"){const decision=rules.update(frame,cut);frame.quality=decision.quality;events.push(...decision.new_events);}
        frames.push(frame);draw(frame);$("progress").value=(index+1)/total;
        const elapsed=(performance.now()-started)/1000,remaining=elapsed/(index+1)*(total-index-1);
        $("status").textContent=`Đang phân tích ${index+1}/${total} mẫu (${((index+1)/total*100).toFixed(0)}%) · ${time.toFixed(2)}/${video.duration.toFixed(2)}s video\nĐã chạy ${elapsed.toFixed(0)}s · còn khoảng ${remaining.toFixed(0)}s · ${events.length} mốc nghi va chạm`;
      }
      const elapsed=(performance.now()-started)/1000;
      $("status").textContent="Đang hoàn tất hồ sơ…";
      const hash=[...new Uint8Array(await crypto.subtle.digest("SHA-256",await file.arrayBuffer()))].map(b=>b.toString(16).padStart(2,"0")).join("");if(generation!==token)return;
      result={schema_version:1,artifact_type:"browser_video_analysis",complete:true,file:{name:file.name,bytes:file.size,sha256:hash,duration_s:video.duration,width:video.videoWidth,height:video.videoHeight},method:{mode,model:metadata,tracker:mode==="detection"?null:"browser_iou_velocity_v1",rules:mode==="collision"?config.rules:null,sampling_hz:20,original_source_fps_verified:false,preprocessing:"canvas RGB letterbox 640x640",runtime:"onnxruntime-web 1.23.2 WASM single thread"},experimental:true,independent_accuracy_evaluated:false,source_seconds_verified:false,score_is_probability:false,processed_samples:frames.length,elapsed_s:elapsed,frames,events};
      const observations=frames.reduce((n,f)=>n+f.observations.length,0),ids=new Set(frames.flatMap(f=>f.observations.map(o=>o.track_id).filter(x=>x!=null)));
      $("status").textContent="Phân tích hoàn tất. Phát video bên trái để xem lại khung bên phải.";
      $("summary").textContent=`${file.name} · ${frames.length} mẫu hình ở 20 Hz · ${observations} lượt bbox · ${ids.size} ID tạm · ${elapsed.toFixed(1)}s xử lý trên thiết bị. ${mode==="collision"?`${events.length} mốc nghi va chạm cần kiểm tra.`:"Chế độ này không kiểm tra va chạm."} Tải JSON để giữ kết quả.`;
      $("events").replaceChildren(...events.map(event=>{const button=document.createElement("button");button.className="small-button";button.textContent=`Nghi va chạm ${event.video_time_s.toFixed(2)}s · #${event.track_ids.join(" + #")}`;button.onclick=()=>{video.pause();video.currentTime=event.video_time_s;};return button;}));
      $("download-json").disabled=$("download-image").disabled=false;busy=false;controls();await seek(0);repaint();
    }catch(error){if(generation===token){terminate("Dừng vì lỗi.");result=null;$("download-json").disabled=$("download-image").disabled=true;$("events").replaceChildren();failure(error.message);$("status").textContent="Chưa hoàn tất phân tích. Có thể chọn lại video hoặc thử clip ngắn hơn.";}}
    finally{if(generation===token){busy=false;controls();}}
  });
  function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
  $("download-json").onclick=()=>{if(result)download(new Blob([JSON.stringify(result)],{type:"application/json"}),"traffic-analysis.json");};
  $("download-image").onclick=()=>{if(result)canvas.toBlob(blob=>{if(blob)download(blob,"traffic-frame.png");},"image/png");};
  window.addEventListener("beforeunload",()=>{if(sourceURL)URL.revokeObjectURL(sourceURL);if(worker)worker.terminate();});
})();
