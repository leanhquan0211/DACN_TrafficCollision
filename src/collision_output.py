"""Render automatic experimental alerts and export hashed evidence after the run."""
from pathlib import Path
import shutil
import subprocess

from src.data_preparation import sha256_file


def draw_alerts(image, events, index, hold_frames=50):
    import cv2
    active = [e for e in events if 0 <= index-e['frame_index'] <= hold_frames]
    for event in active:
        x1,y1,x2,y2 = map(round,event['bbox_xyxy'])
        cv2.rectangle(image,(x1,y1),(x2,y2),(45,45,245),3)
        label = f"{event['event_id']} SUSPECTED COLLISION"
        cv2.putText(image,label,(max(5,x1),max(30,y1-9)),cv2.FONT_HERSHEY_SIMPLEX,.6,(45,45,245),2)
    if active:
        cv2.rectangle(image,(0,0),(image.shape[1],38),(35,35,170),-1)
        cv2.putText(image,'AUTOMATIC ALERT - EXPERIMENTAL / REVIEW REQUIRED',(12,26),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
    return image


def export_evidence(source, rendered, events, config, fps, total_frames):
    import cv2
    capture = cv2.VideoCapture(str(source))
    folder = rendered.parent / (rendered.stem+'_evidence')
    if events:
        folder.mkdir(exist_ok=False)
    evidence = []
    try:
        for event in events:
            capture.set(cv2.CAP_PROP_POS_FRAMES,event['frame_index'])
            ok,image = capture.read()
            if not ok:
                raise ValueError('Cannot read alert evidence frame')
            draw_alerts(image,[event],event['frame_index'])
            snapshot = folder / f"{event['event_id']}.jpg"
            if not cv2.imwrite(str(snapshot),image):
                raise OSError('Cannot save event snapshot')
            rendered_time = event['frame_index']/fps
            start = max(0,rendered_time-config['evidence_before_video_s'])
            duration = min(total_frames/fps,rendered_time+config['evidence_after_video_s'])-start
            clip = folder / f"{event['event_id']}.mp4"
            subprocess.run([shutil.which('ffmpeg') or 'ffmpeg','-hide_banner','-loglevel','error','-n',
                            '-ss',str(start),'-i',str(rendered),'-t',str(duration),'-an','-c:v','libx264',
                            '-preset','veryfast','-crf','22','-movflags','+faststart',str(clip)],check=True,
                           stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            evidence.append(dict(**event,snapshot=str(snapshot.relative_to(rendered.parent)),
                                 snapshot_sha256=sha256_file(snapshot),clip=str(clip.relative_to(rendered.parent)),
                                 clip_sha256=sha256_file(clip),clip_start_video_s=start,clip_duration_video_s=duration,
                                 annotated_video_time_s=rendered_time,
                                 includes_post_alert_context=True,post_alert_context_used_for_decision=False))
    finally:
        capture.release()
    return evidence
