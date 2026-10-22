"""Personal, aspect-correct pinch calibration layered on upstream HandTracker.

Upstream already supplies scale normalization, hysteresis, debounce and adaptive
position filtering. This extension learns personal thresholds from prompted
samples, rejects overlapping calibration data, and requires release after loss.
"""
from collections import deque
import json
import math
from pathlib import Path
import time
import os
import numpy as np
from aeropuzzle.hand_tracking import HandTracker, _hand_scale

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'results'
RESULTS.mkdir(exist_ok=True)


def pixel_ratio(hand, width, height):
    def distance(i,j):
        return math.hypot((hand[i].x-hand[j].x)*width,(hand[i].y-hand[j].y)*height)
    palm = distance(0,9)
    if palm < 25 or not all(math.isfinite(v) for p in hand for v in (p.x,p.y)):
        return None
    ratio=distance(4,8)/palm
    return ratio if 0<=ratio<=4 else None


def fit_profile(open_samples, closed_samples, label):
    if min(len(open_samples),len(closed_samples)) < 25:
        raise ValueError('Need at least 25 valid samples per pose. Face your palm toward the camera and retry.')
    open_low=float(np.percentile(open_samples,10))
    closed_high=float(np.percentile(closed_samples,90))
    gap=open_low-closed_high
    if gap < .08:
        raise ValueError('Open and pinched samples overlap. Spread thumb/index more for OPEN, then touch them for PINCH.')
    return dict(hand=label,close_ratio=closed_high+.35*gap,open_ratio=closed_high+.65*gap,
                open_p10=open_low,closed_p90=closed_high,separation=gap,
                open_n=len(open_samples),closed_n=len(closed_samples),
                metric='thumb-index pixel distance / wrist-middle-MCP pixel distance',
                validation='Prompted calibration sample separation; NOT independent recognition accuracy',
                recorded_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))


class CalibratedHandTracker(HandTracker):
    def __init__(self):
        super().__init__()
        self.profile=None
        self.phase='idle'
        self.phase_started=0.
        self.phase_samples=[]
        self.open_samples=[]
        self.closed_samples=[]
        self.calibration_label=None
        self.message='C: calibrate your pinch; O: open sample; K: pinched sample'
        self.ratio=None
        self.require_release=True
        self.width,self.height=1280,720
        self.frames=0;self.hand_frames=0;self.pinch_frames=0;self.losses=0
        self.inference_ms=deque(maxlen=1800)
        self.last_detected=False
        self.last_pinch=False
        self.raw_history=deque(maxlen=30)
        self.last_saved=0.
        self.started=time.monotonic()

    @property
    def calibrating(self):
        return self.phase!='idle'

    def label(self,index):
        try:return self.results.handedness[index][0].category_name
        except (IndexError,AttributeError):return 'Unknown'

    def control_index(self):
        if not self.results or not self.results.hand_landmarks:return None
        desired=self.calibration_label if self.calibrating else (self.profile['hand'] if self.profile else None)
        indices=list(range(len(self.results.hand_landmarks)))
        if desired:
            return next((i for i in indices if self.label(i)==desired),None)
        return max(indices,key=lambda i:_hand_scale(self.results.hand_landmarks[i]))

    def handle_key(self,key):
        if key in (ord('c'),ord('C')):
            self.phase='ready_open';self.calibration_label=None
            self.open_samples=[];self.closed_samples=[];self.require_release=True
            self.message='Show ONE open hand, spread thumb/index. Press O to sample for 3 seconds.'
        elif key in (ord('o'),ord('O')) and self.phase=='ready_open':
            self._begin('open')
        elif key in (ord('k'),ord('K')) and self.phase=='ready_closed':
            self._begin('closed')
        elif key in (ord('x'),ord('X')):
            self.phase='idle';self.profile=None;self.require_release=True
            self.message='Upstream default controller restored. C starts personal calibration.'
        elif key in (ord('l'),ord('L')):
            path=RESULTS/'personal_calibration.json'
            if path.exists():
                try:
                    profile=json.loads(path.read_text())
                    if not 0<profile['close_ratio']<profile['open_ratio']<5:raise ValueError('Invalid thresholds')
                    self.profile=profile;self.phase='idle';self.require_release=True
                    self.message=f"Loaded personal {profile['hand']} profile; open that hand to arm."
                except (ValueError,KeyError,TypeError):self.message='Saved profile invalid; press C to recalibrate.'
            else:self.message='No saved calibration. Press C to create one.'

    def _begin(self,phase):
        idx=self.control_index()
        if idx is None:
            self.message='No suitable hand. Show one hand clearly and press the sample key again.'
            return
        self.calibration_label=self.label(idx)
        self.phase=phase;self.phase_started=time.monotonic();self.phase_samples=[]
        self.message=f"Sampling {phase.upper()} for 3 seconds. Hold your {self.calibration_label} hand steady."

    def _advance(self):
        if self.phase not in ('open','closed'):return
        if self.ratio is not None:self.phase_samples.append(self.ratio)
        if time.monotonic()-self.phase_started<3:return
        if self.phase=='open':
            self.open_samples=self.phase_samples.copy();self.phase='ready_closed'
            self.message=f'OPEN: {len(self.open_samples)} samples. Touch thumb/index and press K to sample PINCH.'
        else:
            self.closed_samples=self.phase_samples.copy()
            try:
                self.profile=fit_profile(self.open_samples,self.closed_samples,self.calibration_label)
                (RESULTS/'personal_calibration.json').write_text(json.dumps(self.profile,indent=2))
                (RESULTS/'calibration_samples.json').write_text(json.dumps(dict(open=self.open_samples,closed=self.closed_samples),indent=2))
                self.phase='idle';self.require_release=True
                self._pinch_state={'Left':False,'Right':False};self._pinch_start_time={'Left':0.,'Right':0.}
                self.message=f"Calibrated {self.profile['hand']}: close {self.profile['close_ratio']:.2f}, release {self.profile['open_ratio']:.2f}. OPEN your hand to arm."
            except ValueError as exc:
                self.phase='ready_open';self.calibration_label=None
                self.message=str(exc)+' Press O to retry OPEN.'

    def find_hands(self,frame):
        self.height,self.width=frame.shape[:2]
        small=frame if self.width<=640 else __import__('cv2').resize(frame,(640,round(self.height*640/self.width)))
        tick=time.perf_counter();super().find_hands(small)
        self.inference_ms.append((time.perf_counter()-tick)*1000)
        self.frames+=1
        idx=self.control_index()
        detected=idx is not None
        self.hand_frames+=int(detected)
        if self.last_detected and not detected:self.losses+=1
        if not detected:
            self.require_release=True;self.ratio=None;self.raw_history.clear()
        else:
            hand=self.results.hand_landmarks[idx]
            self.ratio=pixel_ratio(hand,self.width,self.height)
            if self.ratio is not None:self.raw_history.append(self.ratio)
        self.last_detected=detected
        if detected and self.frames%30==0 and os.environ.get('AEROPUZZLE_EVIDENCE')=='1':
            __import__('cv2').imwrite(str(RESULTS/'live_hand_input_local.jpg'),frame)
        self._advance()
        if time.monotonic()-self.last_saved>2:
            self.save();self.last_saved=time.monotonic()

    def _update_pinch_for_hand(self,hand,idx):
        if not self.profile:return super()._update_pinch_for_hand(hand,idx)
        label=self.label(idx)
        mx=(hand[4].x+hand[8].x)/2;my=(hand[4].y+hand[8].y)/2
        if label!=self.profile['hand']:return False,mx,my
        ratio=pixel_ratio(hand,self.width,self.height)
        if ratio is None:
            self._pinch_state[label]=False
            return False,mx,my
        now=time.monotonic()
        if self._pinch_state.get(label,False):
            if ratio>self.profile['open_ratio']:self._pinch_state[label]=False
        elif ratio<self.profile['close_ratio']:
            if self._pinch_start_time.get(label,0.)==0.:self._pinch_start_time[label]=now
            elif now-self._pinch_start_time[label]>=self.PINCH_CONFIRM_DELAY:self._pinch_state[label]=True
        else:self._pinch_start_time[label]=0.
        return self._pinch_state.get(label,False),mx,my

    def get_pinch(self):
        result=super().get_pinch()
        idx=self.control_index()
        if idx is None or self.ratio is None or self.calibrating:
            if idx is None or self.ratio is None:self.require_release=True
            self.last_pinch=False
            return False,result[1],result[2]
        if self.require_release:
            threshold=self.profile['open_ratio'] if self.profile else .6
            if self.ratio is not None and self.ratio>threshold:self.require_release=False
            self.last_pinch=False
            return False,result[1],result[2]
        self.last_pinch=result[0];self.pinch_frames+=int(result[0])
        return result

    def get_index_pos(self):
        idx=self.control_index()
        if idx is None or self.ratio is None:return False,0,0
        point=self.results.hand_landmarks[idx][8]
        return True,point.x,point.y

    def save(self):
        report=dict(frames=self.frames,hand_frames=self.hand_frames,tracking_losses=self.losses,
                    elapsed_s=time.monotonic()-self.started,observed_loop_fps=self.frames/max(time.monotonic()-self.started,.001),
                    pinching_frames=self.pinch_frames,inference_p50_ms=float(np.median(self.inference_ms)) if self.inference_ms else None,
                    inference_p95_ms=float(np.percentile(self.inference_ms,95)) if self.inference_ms else None,
                    profile=self.profile,calibration_phase=self.phase,
                    note='Tracking coverage and calibration separation are not labeled recognition accuracy.')
        (RESULTS/'live_tracking.json').write_text(json.dumps(report,indent=2))

    def draw_status(self,frame):
        import cv2
        h,w=frame.shape[:2]
        overlay=frame.copy();cv2.rectangle(overlay,(24,h-126),(w-24,h-64),(20,24,33),-1)
        cv2.addWeighted(overlay,.88,frame,.12,0,frame)
        p50=float(np.median(self.inference_ms)) if self.inference_ms else 0
        mode=f"PERSONAL {self.profile['hand']}" if self.profile else 'UPSTREAM DEFAULT'
        thresholds=f" | close {self.profile['close_ratio']:.2f}/release {self.profile['open_ratio']:.2f}" if self.profile else ''
        status='RELEASE TO ARM' if self.require_release else ('PINCH' if self.last_pinch else 'READY')
        ratio=f'{self.ratio:.2f}' if self.ratio is not None else '--'
        cv2.putText(frame,f'{mode} | {status} | ratio {ratio}{thresholds} | model {p50:.0f} ms',(38,h-101),cv2.FONT_HERSHEY_SIMPLEX,.57,(220,240,240),1,cv2.LINE_AA)
        cv2.putText(frame,self.message[:144],(38,h-78),cv2.FONT_HERSHEY_SIMPLEX,.49,(100,235,210),1,cv2.LINE_AA)
        return frame
