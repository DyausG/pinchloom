"""Actual-loop UI/difficulty regressions. Scripted inputs, never live inference."""
from pathlib import Path
from types import SimpleNamespace
from collections import deque
import json
import os
import sys
import time
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aeropuzzle_game'))
from aeropuzzle import app
from aeropuzzle.ui_skin import Skin,control_state,WINDOW_TITLE,text_sprite
from aeropuzzle.support import MouseTracker,sample_board

OUT=ROOT/'results'/'scripted'
OUT.mkdir(parents=True,exist_ok=True)
os.environ['PINCHLOOM_RUN_DIR']=str(OUT)
os.environ.pop('PINCHLOOM_CAPTURE',None)
records=[]
def test(name,fn):
    try:detail=fn();records.append(dict(name=name,passed=True,detail=detail))
    except Exception as e:records.append(dict(name=name,passed=False,error=repr(e)))
    print(records[-1],flush=True)

def loop(actions,mouse=True):
    events=[];index=[0];frames=[];trackers=[];created=[];windows=[]
    funcs=('namedWindow','resizeWindow','setMouseCallback','imshow','waitKey','getWindowProperty','destroyAllWindows','VideoCapture')
    old={k:getattr(cv2,k) for k in funcs}; old_event=app.event;old_factory=app.CalibratedHandTracker
    old_mouse=app.MouseTracker;old_create=app.Puzzle.create
    class ScriptTracker(MouseTracker):
        def __init__(self):
            super().__init__();self.calibrating=False;self.ratio=.8;self.hand_frames=1
            self.inference_ms=deque();self.phase='idle';self.phase_samples=[];trackers.append(self)
        def handle_key(self,key):
            if key==ord('c'):self.calibrating=True
            elif key==ord('x'):self.calibrating=False
    class Camera:
        def set(self,*a):pass
        def isOpened(self):return True
        def read(self):return True,sample_board().copy()
        def release(self):pass
    def create(p,image):
        created.append(dict(grid=p.grid_size,shape=list(image.shape),image=image.copy()))
        return old_create(p,image)
    cv2.VideoCapture=lambda *a:Camera()
    app.MouseTracker=ScriptTracker;app.CalibratedHandTracker=ScriptTracker
    app.Puzzle.create=create;app.event=lambda kind,**kw:events.append(dict(event=kind,**kw))
    cv2.namedWindow=lambda name,*a:windows.append(name)
    cv2.resizeWindow=lambda name,*a:windows.append(name)
    cv2.setMouseCallback=lambda name,fn:windows.append(name)
    cv2.imshow=lambda name,img:(windows.append(name),frames.append(img.copy()))
    cv2.getWindowProperty=lambda name,*a:(windows.append(name) or 1)
    cv2.destroyAllWindows=lambda:None
    def wait(delay):
        i=index[0];index[0]+=1
        if i>=len(actions):return 27
        a=actions[i]
        if isinstance(a,str):return ord(a)
        if callable(a):a(trackers[0]);return 255
        return a
    cv2.waitKey=wait
    try:app.main(mouse=mouse)
    finally:
        for k,v in old.items():setattr(cv2,k,v)
        app.event=old_event;app.CalibratedHandTracker=old_factory;app.MouseTracker=old_mouse;app.Puzzle.create=old_create
    assert all(n==WINDOW_TITLE for n in windows)
    return events,frames,created

def pointer(event,x,y):
    return lambda t:t.mouse_event(event,x,y,0,None)

def difficulty():
    d=cv2.EVENT_LBUTTONDOWN;m=cv2.EVENT_MOUSEMOVE;u=cv2.EVENT_LBUTTONUP
    actions=['2','3','2','d',pointer(d,448,228),pointer(m,832,228),pointer(u,832,228),255,'3','r','3','d',pointer(d,384,195),pointer(m,640,195),pointer(u,640,195),255,'r','2','n','3']
    events,frames,created=loop(actions)
    sizes=[e['grid'] for e in events if e['event']=='difficulty_selected']
    assert sizes==[2,3,2,3,2],events
    assert [c['grid'] for c in created]==[2,3,2]
    wins=[e for e in events if e['event']=='solved'];assert len(wins)==2 and all(e['moves']==1 for e in wins)
    assert sum(e['event']=='difficulty_ignored' for e in events)==2
    assert not any(e['event']=='solved' for e in events[:4]),'Demo auto-won'
    cv2.imwrite(str(OUT/'mouse_victory_2x2.png'),frames[8])
    cv2.imwrite(str(OUT/'mouse_victory_3x3.png'),frames[16])
    cv2.imwrite(str(OUT/'start_2x2.png'),frames[1])
    return dict(selected=sizes,round_grids=[c['grid'] for c in created],wins=len(wins),events=events)

def calibration_guard():
    # Inject only calibration-active flag; tests guard, NOT calibration inference.
    events,_,_=loop(['2',lambda t:setattr(t,'calibrating',True),'3',lambda t:setattr(t,'calibrating',False),'3'])
    assert [e['grid'] for e in events if e['event']=='difficulty_selected']==[2,3]
    assert any(e['event']=='difficulty_ignored' and e['reason']=='calibration active' for e in events)
    return events

def camera_source():
    events,frames,created=loop(['2',32,'r','3',32],mouse=False)
    assert [c['grid'] for c in created]==[2,3]
    # Fake camera pixels verify geometry and clean capture, not webcam/model.
    original=cv2.flip(sample_board(),1)
    h,w=original.shape[:2]
    expected=original[int(h*.18):int(h*.73),int(w*.2):int(w*.8)]
    assert all(np.array_equal(c['image'],expected) for c in created)
    return dict(round_grids=[c['grid'] for c in created],source='synthetic camera stub; exact clean central crop verified')

def states_and_geometry():
    tracker=SimpleNamespace(calibrating=False,profile=None,require_release=True,hand_frames=0,ratio=None,
        inference_ms=deque(),message='C: calibrate; O: open; K: pinch',phase='idle')
    assert control_state(tracker,False,False,False,False)[0]=='NO VALID HAND'
    tracker.hand_frames=1;assert control_state(tracker,False,False,False,False)[0]=='TRACKING LOST'
    assert control_state(tracker,False,True,False,False)[0]=='OPEN TO ARM'
    tracker.require_release=False;tracker.ratio=1.
    assert control_state(tracker,False,True,False,False)[0]=='OPEN / READY'
    assert control_state(tracker,False,True,True,False)[0]=='PINCHING'
    assert control_state(tracker,False,True,True,True)[0]=='GRABBED'
    skin=Skin();timings=[]
    for w,h in ((1280,720),(640,480),(960,540)):
        board=(int(w*.2),int(h*.18),int(w*.8),int(h*.73))
        image=np.full((h,w,3),150,np.uint8);before=image[board[1]:board[3],board[0]:board[2]].copy()
        for _ in range(25):
            frame=image.copy();skin.compose(frame,tracker=tracker,mouse=False,mode='puzzle',grid=2,
                round_kind='shuffled sample',moves=3,correct=1,start_time=time.time()-10,end_time=None,
                solved=False,shuffling=False,detected=True,pinch=False,dragging=False,two_hands=False,board=board)
            assert np.array_equal(before,frame[board[1]:board[3],board[0]:board[2]]),'UI covers playable pixels'
            if w==1280:timings.append(skin.last_ui_ms)
    # Almost-full-frame arbitrary crop must suppress intersecting HUD panels.
    w,h=1280,720;board=(5,5,1275,715);frame=np.full((h,w,3),150,np.uint8)
    skin.compose(frame,tracker=tracker,mouse=False,mode='puzzle',grid=3,round_kind='camera',moves=0,correct=0,
        start_time=None,end_time=None,solved=False,shuffling=False,detected=True,pinch=False,dragging=False,two_hands=False,board=board)
    assert np.all(frame[5:715,5:1275]==150),'Large crop overdraw'
    assert text_sprite.cache_info().maxsize==512
    return dict(states='no-hand/lost/rearm/open/pinch/grab checked',board_pixels_preserved=True,
                sizes=[[1280,720],[640,480],[960,540]],isolated_ui_p50_ms=float(np.median(timings)),
                isolated_ui_p95_ms=float(np.percentile(timings,95)),note='Synthetic render timing, not live full-loop FPS')

test('Grid selection, active-round rejection, two real-loop mouse wins',difficulty)
test('Difficulty ignored during calibration',calibration_guard)
test('Both grids preserve clean camera-puzzle capture',camera_source)
test('Honest UI states, scaling and arbitrary-crop non-occlusion',states_and_geometry)
(OUT/'new_regressions.json').write_text(json.dumps(dict(records=records,failures=sum(not r['passed'] for r in records)),indent=2))
raise SystemExit(any(not r['passed'] for r in records))
