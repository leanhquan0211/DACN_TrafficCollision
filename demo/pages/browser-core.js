/* Browser deployment helpers. The browser tracker is distinct from ByteTrack. */
"use strict";
(function (scope) {
  const center = b => [(b[0]+b[2])/2,(b[1]+b[3])/2];
  const diag = b => Math.hypot(b[2]-b[0],b[3]-b[1]);
  const distance = (a,b) => Math.hypot(a[0]-b[0],a[1]-b[1]);
  const median = values => { const a=[...values].sort((x,y)=>x-y),m=a.length>>1; return a.length%2?a[m]:(a[m-1]+a[m])/2; };
  function interaction(a,b) {
    const inter=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));
    const area=Math.min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]));
    const gap=Math.hypot(Math.max(0,a[0]-b[2],b[0]-a[2]),Math.max(0,a[1]-b[3],b[1]-a[3]));
    return [area>0?inter/area:0,gap/Math.max(1,(diag(a)+diag(b))/2)];
  }
  function iou(a,b) {
    const inter=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));
    return inter/Math.max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter);
  }
  const classNames={1:"bicycle",2:"car",3:"motorcycle",5:"bus",7:"truck"};
  function decode(data,dims,width,height,confidence=.25,nms=.7) {
    if (dims.length!==3||dims[0]!==1||dims[1]!==84) throw new Error("Đầu ra mô hình không đúng [1,84,N].");
    const n=dims[2],scale=Math.min(640/width,640/height),rw=Math.round(width*scale),rh=Math.round(height*scale);
    const left=Math.round((640-rw)/2-.1),top=Math.round((640-rh)/2-.1),boxes=[];
    for(let i=0;i<n;i++) {
      let score=0,cls=-1;
      for(let c=0;c<80;c++) if(data[(4+c)*n+i]>score){score=data[(4+c)*n+i];cls=c;}
      if(score<confidence||!classNames[cls])continue;
      const x=data[i],y=data[n+i],w=data[2*n+i],h=data[3*n+i];
      const b=[Math.max(0,(x-w/2-left)/scale),Math.max(0,(y-h/2-top)/scale),Math.min(width,(x+w/2-left)/scale),Math.min(height,(y+h/2-top)/scale)];
      if(b.every(Number.isFinite)&&b[2]>b[0]&&b[3]>b[1])boxes.push({bbox_xyxy:b,confidence:score,class_id:cls,class_name:classNames[cls],track_id:null,missing_mask:0});
    }
    boxes.sort((a,b)=>b.confidence-a.confidence);
    const kept=[];
    for(const box of boxes) {if(!kept.some(k=>iou(k.bbox_xyxy,box.bbox_xyxy)>nms))kept.push(box);if(kept.length===100)break;}
    return kept;
  }
  class Tracker {
    constructor(){this.tracks=new Map();this.next=1;}
    reset(){this.tracks.clear();} // Never reuse an old ID after a cut.
    update(observations,index) {
      for(const [id,t] of this.tracks)if(index-t.index>3)this.tracks.delete(id);
      const links=[];
      for(const [id,t] of this.tracks) {
        const dt=index-t.index,pred=t.box.map((v,k)=>v+t.velocity[k]*dt);
        observations.forEach((o,j)=>{const score=iou(pred,o.bbox_xyxy);if(score>=.3)links.push({id,j,score});});
      }
      links.sort((a,b)=>b.score-a.score);const used=new Set(),assigned=new Map();
      for(const l of links)if(!used.has(l.id)&&!assigned.has(l.j)){used.add(l.id);assigned.set(l.j,l.id);}
      return observations.map((o,j)=>{
        const id=assigned.get(j)||this.next++,old=this.tracks.get(id),box=o.bbox_xyxy;
        const velocity=old?box.map((v,k)=>.5*old.velocity[k]+.5*(v-old.box[k])/(index-old.index)):[0,0,0,0];
        const age=(old?.age||0)+1;this.tracks.set(id,{box:[...box],velocity,index,age});
        return {...o,track_id:id,track_age_observations:age};
      });
    }
  }
  function velocity(history,end,window) {
    const points=history.filter(p=>end-window<=p[0]&&p[0]<=end);
    if(points.length<3||points.at(-1)[0]-points[0][0]<window-1)return null;
    const steps=[];
    for(let i=1;i<points.length;i++){
      const a=points[i-1],b=points[i],dt=b[0]-a[0],ca=center(a[1]),cb=center(b[1]),scale=Math.max(1,(diag(a[1])+diag(b[1]))/2);
      steps.push([(cb[0]-ca[0])/dt/scale,(cb[1]-ca[1])/dt/scale]);
    }
    return [median(steps.map(v=>v[0])),median(steps.map(v=>v[1]))];
  }
  // Direct port of the v5 rule logic, measured separately for the browser path.
  class Rules {
    constructor(config,width=640,height=640){this.cfg={...config};this.scale=640/Math.max(width,height);this.tracks=new Map();this.pairs=new Map();this.events=[];this.next=0;this.lastTime=null;this.segment=0;}
    reset(){this.tracks.clear();this.pairs.clear();this.segment++;}
    features(ids,index,overlap){
      const c=this.cfg,hs=ids.map(id=>this.tracks.get(id));
      if(hs.some(h=>index-h[0][0]<c.minimum_history_frames||median(h.map(p=>p[2]))<c.minimum_history_median_confidence))return null;
      const old=hs.map(h=>velocity(h,index-c.past_motion_offset_frames,c.motion_window_frames)),now=hs.map(h=>velocity(h,index,c.motion_window_frames));
      if([...old,...now].some(v=>v===null))return null;
      const os=old.map(v=>Math.hypot(...v)),ns=now.map(v=>Math.hypot(...v));
      const stop=os.map((p,i)=>p>=c.minimum_prior_speed_body_per_frame&&ns[i]<=p*c.stop_speed_ratio);
      const turn=os.map((p,i)=>p>=c.minimum_prior_speed_body_per_frame&&ns[i]>=c.minimum_turn_speed_body_per_frame&&(old[i][0]*now[i][0]+old[i][1]*now[i][1])/Math.max(1e-12,p*ns[i])<=c.direction_change_cosine);
      const shared=hs[0].map(p=>p[0]).filter(f=>f<=index-c.past_motion_offset_frames&&hs[1].some(p=>p[0]===f));
      if(!shared.length)return null;
      const source=shared[0],before=hs.map(h=>h.find(p=>p[0]===source)[1]),current=hs.map(h=>h.at(-1)[1]);
      const closing=(distance(...before.map(center))-distance(...current.map(center)))/Math.max(1,(diag(current[0])+diag(current[1]))/2);
      const prior=interaction(...before)[0],bottomGap=Math.abs(current[0][3]-current[1][3])/Math.max(1,...[Math.min(...current.map(b=>b[3]-b[1]))]);
      const compatible=c.maximum_bottom_edge_gap_min_height==null||bottomGap<=c.maximum_bottom_edge_gap_min_height;
      const overlapContact=overlap>=c.contact_intersection_over_min;
      const flags={contact:overlapContact&&compatible,new_contact:overlap-prior>=c.contact_increase,approach:closing>=c.approach_body_units,motion_change:stop.some(Boolean)||turn.some(Boolean)};
      return {...flags,evidence_score:Object.values(flags).filter(Boolean).length/4,overlap_contact:overlapContact,bottom_edge_compatible:compatible,bottom_edge_gap_min_height:bottomGap,overlap,prior_overlap:prior,approach_body_units:closing,prior_speed_body_per_frame:os,current_speed_body_per_frame:ns,sudden_stop:stop,direction_change:turn,comparison_frame:source};
    }
    update(frame,sceneCut=false){
      const c=this.cfg,index=frame.frame_index,time=frame.video_time_s;
      if(index!==this.next||!Number.isFinite(time)||(this.lastTime!==null&&time<=this.lastTime))throw new Error("Clock/frame không liên tục.");
      this.next++;this.lastTime=time;if(sceneCut)this.reset();const current=new Map();
      for(const o of frame.observations){
        const id=o.track_id,b=o.bbox_xyxy,side=Math.min(b[2]-b[0],b[3]-b[1]);
        if(id==null||o.missing_mask||o.confidence<c.minimum_confidence||side<c.minimum_box_side_px||side*this.scale<(c.minimum_box_side_inference_px||0))continue;
        if(current.has(id))throw new Error("ID trùng trong frame.");
        let h=this.tracks.get(id);
        if(h&&(index-h.at(-1)[0]>c.maximum_track_gap_frames||Math.max(diag(b)/diag(h.at(-1)[1]),diag(h.at(-1)[1])/diag(b))>c.maximum_box_scale_ratio)){
          h=null;for(const [key,p] of this.pairs)if(p.ids.includes(id))this.pairs.delete(key);
        }
        if(!h){h=[];this.tracks.set(id,h);}h.push([index,[...b],o.confidence]);if(h.length>c.history_frames)h.shift();current.set(id,o);
      }
      for(const [id,h] of this.tracks)if(index-h.at(-1)[0]>c.candidate_expiry_frames)this.tracks.delete(id);
      const ids=[...current.keys()].sort((a,b)=>a-b),candidates=[],newEvents=[];
      for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){
        const pair=[ids[i],ids[j]],a=current.get(pair[0]).bbox_xyxy,b=current.get(pair[1]).bbox_xyxy,[overlap,gap]=interaction(a,b);
        if(gap>c.candidate_gap_body_units)continue;
        const key=pair.join(":"),s=this.pairs.get(key)||{ids:pair,hits:[],last:index,cooldown_until:-1,state:"idle"};this.pairs.set(key,s);s.last=index;
        const f=this.features(pair,index,overlap),hit=!!(f&&f.contact&&f.new_contact&&f.approach&&f.motion_change);
        s.hits.push([index,hit]);s.hits=s.hits.filter(([k])=>index-k<c.confirmation_window_frames).slice(-c.confirmation_window_frames);
        if(index<s.cooldown_until)s.state="cooldown";
        else if(s.hits.filter(p=>p[1]).length>=c.confirmation_hits&&hit){
          s.state="confirmed_by_rule";
          const event={event_id:`event-${String(this.events.length+1).padStart(4,"0")}`,method:c.rule_id,decision:"suspected_collision",automatic:true,needs_review:true,segment:this.segment,frame_index:index,video_time_s:time,source_time_s:frame.source_time_s??null,track_ids:pair,bbox_xyxy:[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])],evidence_score:Math.round(f.evidence_score*1e4)/1e4,score_is_probability:false,features:f,first_support_frame:Math.min(...s.hits.filter(p=>p[1]).map(p=>p[0]))};
          this.events.push(event);newEvents.push(event);s.cooldown_until=index+c.pair_cooldown_frames;s.hits=[];
        }else s.state=s.hits.some(p=>p[1])?"suspected":"idle";
        candidates.push({track_ids:pair,state:s.state,intersection_over_min:overlap,gap_body_units:gap,support:hit,features:f});
      }
      for(const [key,s] of this.pairs)if(index-s.last>c.candidate_expiry_frames)this.pairs.delete(key);
      return {frame_index:index,video_time_s:time,source_time_s:frame.source_time_s??null,scene_cut:sceneCut,segment:this.segment,candidates,new_events:newEvents,quality:{observations:frame.observations.length,eligible_tracks:current.size,abstained_observations:frame.observations.length-current.size}};
    }
  }
  scope.TrafficCore={decode,iou,Tracker,Rules};
})(typeof self!=="undefined"?self:globalThis);
