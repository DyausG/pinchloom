"""Small reliability/fallback helpers for the adapted upstream OpenCV game."""
from functools import lru_cache
import json
from pathlib import Path
import time
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
EVENTS=ROOT/'results'/'game_events.jsonl'


def event(kind,**details):
    with EVENTS.open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),event=kind,**details))+'\n')


def sample_board(grid=3):
    h,w=420,720
    image=np.zeros((h,w,3),np.uint8)
    colors=[(115,65,30),(55,135,55),(50,90,195),(170,90,70),(50,150,185),(155,70,155),(115,150,25),(45,85,115),(130,80,40)]
    for index in range(grid*grid):
        row,col=divmod(index,grid);x0=col*w//grid;y0=row*h//grid;x1=(col+1)*w//grid;y1=(row+1)*h//grid
        cv2.rectangle(image,(x0,y0),(x1,y1),colors[index%len(colors)],-1)
        cv2.rectangle(image,(x0+8,y0+8),(x1-8,y1-8),(220,235,240),2)
        cv2.putText(image,str(index+1),(x0+30,y0+(y1-y0)//2+20),cv2.FONT_HERSHEY_SIMPLEX,2,(255,255,255),4,cv2.LINE_AA)
        cv2.circle(image,(x1-38,y0+35),14+index,(190,230,245),2,cv2.LINE_AA)
    return image


class MouseTracker:
    """Honest input fallback. No landmarks, no model predictions, no fake CV."""
    def __init__(self):
        self.x,self.y=0.,0.;self.down=False;self.width,self.height=1280,720
        self.require_release=False;self.calibrating=False;self.profile=None
        self.message='MOUSE FALLBACK - vision disabled. Drag with left button. N: shuffle; D: one-swap demo.'
    def mouse_event(self,event,x,y,flags,param):
        self.x=x/max(self.width,1);self.y=y/max(self.height,1)
        if event==cv2.EVENT_LBUTTONDOWN:self.down=True
        elif event==cv2.EVENT_LBUTTONUP:self.down=False
    def find_hands(self,frame):self.height,self.width=frame.shape[:2]
    def draw_hands(self,frame):pass
    def get_pinch(self):return self.down,self.x,self.y
    def get_index_pos(self):return True,self.x,self.y
    def get_two_hand_indices(self):return False,(0,0),(0,0)
    def handle_key(self,key):pass
    def save(self):pass
    def draw_status(self,frame):
        h,w=frame.shape[:2]
        cv2.rectangle(frame,(24,h-126),(w-24,h-64),(20,24,33),-1)
        cv2.putText(frame,'MOUSE FALLBACK | CV OFF | camera not required',(38,h-102),cv2.FONT_HERSHEY_SIMPLEX,.65,(90,210,255),2,cv2.LINE_AA)
        cv2.putText(frame,self.message,(38,h-78),cv2.FONT_HERSHEY_SIMPLEX,.48,(220,235,240),1,cv2.LINE_AA)
        return frame
