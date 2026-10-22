"""Pinchloom's read-only OpenCV/Pillow display layer. No control/model changes."""
from functools import lru_cache
from pathlib import Path
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WINDOW_TITLE = 'Pinchloom - Gesture Arcade'
BG=(35,25,16); PANEL=(54,41,28); EDGE=(85,69,52)
INK=(248,245,242); MUTED=(202,188,172)
MINT=(196,226,107); PEACH=(135,190,255)

@lru_cache(maxsize=32)
def font(size,bold=False):
    for name in (['segoeuib.ttf','arialbd.ttf'] if bold else ['segoeui.ttf','arial.ttf']):
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default()

@lru_cache(maxsize=512)
def text_sprite(text,size,color,bold=False):
    f=font(size,bold);box=f.getbbox(text or ' ')
    w=max(1,box[2]-min(0,box[0])+2);h=max(1,box[3]-box[1]+2)
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    d.text((max(0,-box[0]),-box[1]),text,font=f,fill=(*color[::-1],255))
    rgba=np.asarray(im);a=rgba[:,:,3:4].astype(np.uint16)
    return rgba[:,:,:3][:,:,::-1].astype(np.uint16)*a,255-a

def label(im,text,x,y,size=18,color=INK,bold=False):
    fg,inv=text_sprite(str(text),size,color,bold);h,w=fg.shape[:2]
    ih,iw=im.shape[:2];x=int(x);y=int(y)
    x0=max(0,x);y0=max(0,y);x1=min(iw,x+w);y1=min(ih,y+h)
    if x1<=x0 or y1<=y0:return
    part=im[y0:y1,x0:x1];src=(slice(y0-y,y1-y),slice(x0-x,x1-x))
    part[:]=((fg[src]+part.astype(np.uint16)*inv[src]+127)//255).astype(np.uint8)

def panel(im,rect,color=PANEL,radius=12,border=EDGE):
    x1,y1,x2,y2=map(int,rect);h,w=im.shape[:2]
    x1=max(0,x1);y1=max(0,y1);x2=min(w-1,x2);y2=min(h-1,y2)
    if x2<=x1 or y2<=y1:return
    r=max(0,min(radius,(x2-x1)//2,(y2-y1)//2))
    def fill(c,offset=0):
        a,b,cx,dy=x1+offset,y1+offset,x2-offset,y2-offset
        rr=max(0,r-offset)
        cv2.rectangle(im,(a+rr,b),(cx-rr,dy),c,-1)
        cv2.rectangle(im,(a,b+rr),(cx,dy-rr),c,-1)
        for xx,yy in ((a+rr,b+rr),(cx-rr,b+rr),(a+rr,dy-rr),(cx-rr,dy-rr)):
            cv2.circle(im,(xx,yy),rr,c,-1,cv2.LINE_AA)
    if border:fill(border);fill(color,1)
    else:fill(color)

def intersects(a,b):
    return b is not None and a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]

def control_state(tracker,mouse,detected,pinch,dragging):
    if mouse:return ('GRABBED' if dragging else 'MOUSE HELD' if pinch else 'MOUSE READY',PEACH if pinch else MINT)
    if tracker.calibrating:return ('CALIBRATING',PEACH)
    if not detected:
        return ('TRACKING LOST' if getattr(tracker,'hand_frames',0)>0 else 'NO VALID HAND',PEACH)
    if tracker.require_release:return ('OPEN TO ARM',PEACH)
    if dragging:return ('GRABBED',PEACH)
    if pinch:return ('PINCHING',PEACH)
    threshold=tracker.profile['open_ratio'] if tracker.profile else .6
    return ('OPEN / READY' if tracker.ratio is not None and tracker.ratio>threshold else 'READY',MINT)

class Skin:
    def __init__(self):
        self.last_ui_ms=0.
        self.headers={}

    def compose(self,frame,*,tracker,mouse,mode,grid,round_kind,moves,correct,
                start_time,end_time,solved,shuffling,detected,pinch,dragging,
                two_hands,board=None):
        tick=time.perf_counter();h,w=frame.shape[:2]
        sx=w/1280;sy=h/720;scale=min(sx,sy)
        def rect(x1,y1,x2,y2):return tuple(int(v*s) for v,s in zip((x1,y1,x2,y2),(sx,sy,sx,sy)))
        def txt(text,x,y,size=18,color=INK,bold=False):label(frame,text,int(x*sx),int(y*sy),max(10,round(size*scale)),color,bold)
        def card(box):panel(frame,rect(*box),radius=max(3,round(12*scale)))
        active_board=board if mode=='puzzle' else None
        # Darken DISPLAY only, preserving board pixels and all inference geometry.
        if active_board:
            x1,y1,x2,y2=active_board
            regions=(frame[:y1],frame[y2:],frame[y1:y2,:x1],frame[y1:y2,x2:])
        else:regions=(frame,)
        for region in regions:
            if region.size:region[:]=cv2.convertScaleAbs(region,alpha=.48)
        difficulty='BEGINNER 2×2' if grid==2 else 'STANDARD 3×3'
        header=rect(0,0,1280,84)
        if not intersects(header,active_board):
            profile=tracker.profile if not mouse else None
            header_key=(w,h,grid,mouse,profile['hand'] if profile else None)
            header_height=int(84*sy)+1
            cached=self.headers.get(header_key)
            if cached is not None:
                frame[:header_height]=cached
            else:
                cv2.rectangle(frame,(0,0),(w,int(84*sy)),PANEL,-1)
                cv2.ellipse(frame,(int(52*sx),int(43*sy)),(int(20*sx),int(20*sy)),0,35,310,MINT,max(2,round(3*scale)),cv2.LINE_AA)
                cv2.circle(frame,(int(61*sx),int(38*sy)),max(2,round(4*scale)),PEACH,-1,cv2.LINE_AA)
                txt('Pinchloom',90,19,31,INK,True);txt('GESTURE ARCADE',92,56,13,MUTED,True)
                txt('PICTURE SWAP',410,23,16,MUTED,True);txt(difficulty,410,51,15)
                card((845,22,1015,64));txt('MOUSE · CV OFF' if mouse else 'LIVE CAMERA',862,36,16,MINT,True)
                profile=tracker.profile if not mouse else None
                card((1030,22,1248,64));txt('PERSONAL · '+profile['hand'].upper() if profile else 'FALLBACK INPUT' if mouse else 'DEFAULT CONTROL',1044,36,15,PEACH,True)
                if len(self.headers)>=16:self.headers.pop(next(iter(self.headers)))
                self.headers[header_key]=frame[:header_height].copy()
        strip=rect(32,90,1248,119)
        if not intersects(strip,active_board):
            txt('MAKE YOUR MOVE.' if mode=='camera' else round_kind.upper(),32,97,17,MUTED,True)
            txt('2 / 3 select grid before play' if mode=='camera' and not tracker.calibrating else 'R: camera / difficulty' if mode=='puzzle' else 'Calibration active · finish or X to cancel',840,97,16,MUTED)
        if mode=='camera' and not two_hands and (mouse or not detected) and not tracker.calibrating:
            card((256,145,1024,500));txt('Make your move.',292,177,44,INK,True)
            txt('Point, hold left mouse, then release to swap.' if mouse else 'Open to aim. Pinch to grab. Release to swap.',294,246,23,MUTED)
            txt('2  Beginner · 4 larger tiles',294,304,22,MINT,grid==2)
            txt('3  Standard · 9 tiles',650,304,22,MINT,grid==3)
            txt('N   Numbered board       D   One-swap practice',294,361,22)
            txt('R   Return to start          Esc   Quit' if mouse else 'Space   Camera photo     C   Calibrate     L   Load profile',294,408,19)
            txt('Mouse fallback is active. Vision and calibration are disabled.' if mouse else 'Two-hand framing remains available. Show your hands to begin.',294,455,17,MUTED)
        elif mode=='camera' and two_hands:
            if not intersects(rect(32,126,1248,153),board):
                txt('Frame with both index fingers; pinch to capture a photo.',32,131,20,MINT,True)
        if mode=='puzzle':
            metric=rect(1055,145,1248,415)
            elapsed=max(0.,(end_time if solved and end_time else time.time())-start_time) if start_time else 0.
            minutes,seconds=divmod(int(elapsed),60)
            if not intersects(metric,active_board):
                card((1055,145,1248,415));txt('ROUND',1073,163,14,MUTED,True)
                txt(f'{minutes:02}:{seconds:02}',1073,204,35,INK,True)
                txt('elapsed' if not shuffling else 'shuffling…',1073,249,15,MUTED)
                txt(str(moves),1073,291,30,INK,True);txt('moves',1128,303,17,MUTED)
                txt(f'{correct} / {grid*grid}',1073,351,27,MINT,True);txt('tiles in place',1073,389,15,MUTED)
            elif not intersects(rect(32,91,800,121),active_board):
                txt(f'{round_kind.upper()}   ·   {elapsed:.1f}s   ·   {moves} moves   ·   {correct}/{grid*grid} in place',32,96,17)
            if not intersects(rect(32,355,225,500),active_board):
                card((32,355,225,500));txt('HOW TO SWAP',48,374,14,MUTED,True)
                txt('1  Aim with mouse' if mouse else '1  Open to aim',48,409,17)
                txt('2  Hold left button' if mouse else '2  Pinch + move',48,440,17)
                txt('3  Release to swap',48,471,17)
        status,status_color=control_state(tracker,mouse,detected,pinch,dragging)
        if not intersects(rect(32,546,1248,655),active_board):
            card((32,546,1248,655));txt(status,50,560,18,status_color,True)
            if mouse:
                detail='VISION DISABLED · Left mouse button controls the tiles'
                message='Drag, then release over another tile to swap. No hand inference is running.'
            else:
                ratio='—' if tracker.ratio is None else f'{tracker.ratio:.2f}'
                inference=getattr(tracker,'inference_ms',())
                ms=f'{np.median(inference):.0f} ms' if len(inference) else '—'
                detail=f'Ratio {ratio}  ·  Model median {ms}'
                if tracker.profile:detail+=f"  ·  Close {tracker.profile['close_ratio']:.2f} / release {tracker.profile['open_ratio']:.2f}"
                message=tracker.message
                if not tracker.calibrating:
                    if not detected:message='Show the controlling hand clearly. After tracking loss, open it fully before grabbing again.'
                    elif tracker.require_release:message='Open your controlling hand fully to arm. Then aim at a tile and pinch to grab.'
                    elif dragging:message='Tile grabbed. Move over another tile, then release to swap.'
                    elif pinch:message='Pinching. Open your hand, aim at a tile, then pinch again to grab.'
            txt(detail,360,562,16,MUTED)
            if not mouse and tracker.calibrating:
                phase=tracker.phase
                step='1  OPEN' if phase in ('ready_open','open') else '2  PINCH'
                samples=len(tracker.phase_samples) if phase in ('open','closed') else 0
                txt(f'{step}   ·   {samples} valid samples' if phase in ('open','closed') else f'{step}   ·   waiting for sample key',50,592,19,INK,True)
                txt(message,50,624,16,MUTED)
                if phase in ('open','closed'):
                    progress=max(0.,min(1.,(time.monotonic()-tracker.phase_started)/3))
                    cv2.rectangle(frame,(int(750*sx),int(602*sy)),(int(1225*sx),int(608*sy)),EDGE,-1)
                    cv2.rectangle(frame,(int(750*sx),int(602*sy)),(int((750+475*progress)*sx),int(608*sy)),MINT,-1)
            else:
                # Wrap long real recovery messages rather than silently truncate.
                words=message.split();lines=[];line='';f=font(max(10,round(18*scale)))
                for word in words:
                    candidate=(line+' '+word).strip()
                    if f.getlength(candidate)>w-100*sx and line:lines.append(line);line=word
                    else:line=candidate
                if line:lines.append(line)
                for i,line in enumerate(lines[:2]):txt(line,50,592+26*i,18)
                if not mouse and len(lines)<2:txt('C  Calibrate    O  Sample open    K  Sample pinch    L  Load profile    X  Default',50,628,15,MUTED)
        if not intersects(rect(32,665,1248,715),active_board):
            txt('N  New round     D  One-swap     R  Camera     Esc  Quit',34,673,17)
            txt('Adapted from AeroPuzzle',977,674,15,MUTED)
        if solved:
            card((384,218,896,438));txt('Beautifully solved.',418,246,34,MINT,True)
            txt(f'{elapsed:.1f} seconds    ·    {moves} moves    ·    {grid}×{grid}',420,310,22)
            txt('N  New round     D  Practice     R  Camera',420,378,18,MUTED)
        self.last_ui_ms=(time.perf_counter()-tick)*1000
        return frame
