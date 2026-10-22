"""Headless integration of the ACTUAL adapted game loop with callback inputs.
These are scripted inputs, not claimed as human/live gesture gameplay.
"""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aeropuzzle_game'))
import cv2
from aeropuzzle.calibration import fit_profile,pixel_ratio
from aeropuzzle.maze import Puzzle
from aeropuzzle.support import sample_board
from aeropuzzle import app

records=[]
def test(name,fn):
    try:details=fn();records.append(dict(test=name,status='PASS',details=details))
    except Exception as exc:records.append(dict(test=name,status='FAIL',error=repr(exc)))
    print(records[-1],flush=True)

def calibration():
    p=fit_profile(np.linspace(1.1,1.4,60),np.linspace(.07,.15,60),'Right')
    assert .15<p['close_ratio']<p['open_ratio']<1.1
    for a,b in [([1.]*30,[.99]*30),([1.]*10,[.1]*30)]:
        try:fit_profile(a,b,'Right')
        except ValueError:pass
        else:raise AssertionError('Invalid calibration accepted')
    return p

def puzzle():
    outcomes=[]
    for grid in (2,3):
        p=Puzzle(grid);p.create(sample_board(grid))
        p.tiles=p.original_tiles.copy();p.swap(0,1)
        assert not p.is_solved(p.original_tiles)
        p.swap(0,1);assert p.is_solved(p.original_tiles)
        assert p.get_index(0,0)==0 and p.get_index(1,1)==grid*grid-1
        outcomes.append(dict(grid=grid,win_after_correct_swap=True))
    return outcomes

def loop(rounds=2,outside=False,loss=False):
    events=[];callback=[None];counter=[0];last=[None]
    original={name:getattr(cv2,name) for name in ('namedWindow','resizeWindow','setMouseCallback','imshow','waitKey','getWindowProperty','destroyAllWindows')}
    original_event=app.event
    original_index=app.MouseTracker.get_index_pos
    app.MouseTracker.get_index_pos=lambda self:(False,0,0) if getattr(self,'test_hidden',False) else original_index(self)
    app.event=lambda kind,**kw:events.append(dict(event=kind,**kw))
    cv2.namedWindow=lambda *a:None;cv2.resizeWindow=lambda *a:None
    cv2.setMouseCallback=lambda name,fn:callback.__setitem__(0,fn)
    cv2.imshow=lambda name,frame:last.__setitem__(0,frame.copy())
    cv2.getWindowProperty=lambda *a:1
    cv2.destroyAllWindows=lambda:None
    def key(delay):
        i=counter[0];counter[0]+=1
        block=i//5;step=i%5
        if block>=rounds:return 27
        if step==0:return ord('d')
        if step==1:callback[0](cv2.EVENT_LBUTTONDOWN,20 if outside else 384,20 if outside else 195,0,None)
        if step==2:
            callback[0](cv2.EVENT_MOUSEMOVE,640,195,cv2.EVENT_FLAG_LBUTTON,None)
            if loss:callback[0].__self__.test_hidden=True
        if step==3:
            callback[0](cv2.EVENT_LBUTTONUP,640,195,0,None)
            callback[0].__self__.test_hidden=False
        return 255
    cv2.waitKey=key
    try:app.main(mouse=True)
    finally:
        app.event=original_event
        app.MouseTracker.get_index_pos=original_index
        for name,fn in original.items():setattr(cv2,name,fn)
    wins=[e for e in events if e['event']=='solved']
    swaps=[e for e in events if e['event']=='swap']
    if outside or loss:
        assert not swaps and not wins,events
        if loss:assert any(e['event']=='drag_cancelled' for e in events),events
    else:
        assert len(wins)==rounds and all(e['moves']==1 for e in wins),events
        cv2.imwrite(str(ROOT/'results'/'scripted_mouse_victory.jpg'),last[0])
    return dict(rounds=rounds,wins=len(wins),swaps=len(swaps),events=events,input='scripted callbacks; not live hand inference')

test('Personal threshold fit and invalid-data rejection',calibration)
test('Original Puzzle mechanics, two grid sizes',puzzle)
test('Two complete actual-app callback rounds and restart',lambda:loop(2))
test('Out-of-board drag cannot select an edge tile',lambda:loop(1,True))
test('Lost control point cancels a pending drag',lambda:loop(1,loss=True))
(ROOT/'results'/'game_tests.json').write_text(json.dumps(dict(records=records,failures=sum(r['status']=='FAIL' for r in records)),indent=2))
raise SystemExit(any(r['status']=='FAIL' for r in records))
