"use strict";
importScripts("./browser-core.js");
let session,metadata;
async function init(){
  importScripts("./vendor/ort.wasm.min.js");
  ort.env.wasm.numThreads=1;
  ort.env.wasm.wasmPaths=new URL("./vendor/",self.location.href).href;
  const m=await fetch("./models/model.json");if(!m.ok)throw new Error("Không tải được hồ sơ model.");metadata=await m.json();
  const response=await fetch("./models/yolov8n.onnx");if(!response.ok)throw new Error(`Không tải được model (HTTP ${response.status}).`);
  const total=Number(response.headers.get("content-length"))||metadata.bytes;
  const reader=response.body.getReader(),parts=[];let loaded=0;
  while(true){const {value,done}=await reader.read();if(done)break;parts.push(value);loaded+=value.length;postMessage({kind:"model-progress",loaded,total});}
  const bytes=new Uint8Array(loaded);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
  const hash=[...new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))].map(x=>x.toString(16).padStart(2,"0")).join("");
  if(hash!==metadata.sha256)throw new Error("Model sai fingerprint. Tải lại trang để thử lại.");
  session=await ort.InferenceSession.create(bytes,{executionProviders:["wasm"],graphOptimizationLevel:"all"});
  postMessage({kind:"ready",metadata});
}
self.onmessage=async ({data})=>{
  try{
    if(data.kind==="init"){await init();return;}
    if(!session)throw new Error("Model chưa sẵn sàng.");
    const pixels=new Uint8ClampedArray(data.pixels),plane=640*640,input=new Float32Array(3*plane);
    for(let i=0;i<plane;i++){input[i]=pixels[4*i]/255;input[plane+i]=pixels[4*i+1]/255;input[2*plane+i]=pixels[4*i+2]/255;}
    const tensor=new ort.Tensor("float32",input,[1,3,640,640]);
    const outputs=await session.run({[session.inputNames[0]]:tensor});
    const out=outputs[session.outputNames[0]];
    const observations=TrafficCore.decode(out.data,out.dims,data.width,data.height,.25,.7);
    for(const value of Object.values(outputs))value.dispose();tensor.dispose();
    postMessage({kind:"result",id:data.id,observations});
  }catch(error){postMessage({kind:"error",message:error.message||String(error)});}
};
