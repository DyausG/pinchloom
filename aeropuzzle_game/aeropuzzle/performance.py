"""Measured application timing; no inference/control modifications."""
from collections import deque
from pathlib import Path
import json
import os
import time
import numpy as np

class Performance:
    def __init__(self):
        self.started=time.perf_counter();self.last_saved=self.started
        self.frames=0;self.render=deque(maxlen=1800);self.ui=deque(maxlen=1800)
        self.folder=Path(os.environ.get('PINCHLOOM_RUN_DIR',str(Path(__file__).resolve().parents[2]/'results'/'pinchloom_latest')))
        self.folder.mkdir(parents=True,exist_ok=True)
        self.capture_at={}
    def capture(self,frame,mode,tracker,mouse,round_kind,solved):
        if os.environ.get('PINCHLOOM_CAPTURE')!='1':return
        import cv2
        state='mouse' if mouse else 'start' if mode=='camera' else 'puzzle'
        if tracker.calibrating:state='calibration_'+getattr(tracker,'phase','active')
        elif solved:state='victory_mouse' if mouse else 'victory'
        elif round_kind=='one-swap demo' and mode=='puzzle':state='one_swap_mouse' if mouse else 'one_swap'
        elif tracker.profile and not mouse:state='personal_profile'
        if time.monotonic()-self.capture_at.get(state,0)<2:return
        cv2.imwrite(str(self.folder/(state+'.png')),frame)
        self.capture_at[state]=time.monotonic()
    def record(self,render_ms,ui_ms):
        self.frames+=1;self.render.append(render_ms);self.ui.append(ui_ms)
        if time.perf_counter()-self.last_saved>=3:self.save()
    def save(self):
        elapsed=time.perf_counter()-self.started
        report=dict(frames=self.frames,elapsed_s=elapsed,full_loop_fps=self.frames/max(elapsed,.001),
                    update_render_p50_ms=float(np.median(self.render)) if self.render else None,
                    update_render_p95_ms=float(np.percentile(self.render,95)) if self.render else None,
                    ui_p50_ms=float(np.median(self.ui)) if self.ui else None,
                    ui_p95_ms=float(np.percentile(self.ui,95)) if self.ui else None,
                    note='Update/render includes game logic and window submission, excludes inference/capture and waitKey. UI is compose only. FPS is complete session; not motion-to-display latency.')
        (self.folder/'performance.json').write_text(json.dumps(report,indent=2))
        self.last_saved=time.perf_counter()
