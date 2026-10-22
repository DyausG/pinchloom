import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import time
import random
import numpy as np
from aeropuzzle.maze import Puzzle
from aeropuzzle.calibration import CalibratedHandTracker
from aeropuzzle.support import MouseTracker, sample_board, event
from aeropuzzle.ui_skin import Skin, WINDOW_TITLE, MINT, PEACH, INK
from aeropuzzle.performance import Performance


def inside_box(px, py, x1, y1, x2, y2, w, h):
    fx = px * w
    fy = py * h
    return x1 <= fx <= x2 and y1 <= fy <= y2


def to_local(px, py, x1, y1, x2, y2, w, h):
    fx = px * w
    fy = py * h

    if fx < x1 or fx > x2 or fy < y1 or fy > y2:
        return None

    lx = (fx - x1) / (x2 - x1)
    ly = (fy - y1) / (y2 - y1)

    return lx, ly


def draw_grid(img, x1, y1, x2, y2, rows=3, cols=3):
    cell_w = (x2 - x1) // cols
    cell_h = (y2 - y1) // rows

    # Neon blue/cyan grids (254, 242, 0 is BGR for #00f2fe)
    for i in range(1, cols):
        cv2.line(img, (x1 + i*cell_w, y1), (x1 + i*cell_w, y2), MINT, 2)

    for i in range(1, rows):
        cv2.line(img, (x1, y1 + i*cell_h), (x2, y1 + i*cell_h), MINT, 2)


# ================= MAIN ENTRY POINT =================
def main(mouse=False,grid_size=3,camera_index=0):
    # ================= CAMERA =================
    cap = None if mouse else cv2.VideoCapture(camera_index,cv2.CAP_DSHOW)
    if cap is not None:
        cap.set(3,1280);cap.set(4,720)
        if not cap.isOpened():
            cap.release();cap=None;mouse=True
            print('Camera unavailable: MOUSE FALLBACK, vision disabled.',flush=True)

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    # Fit common Windows DPI scaling; only the window changes, never camera pixels.
    cv2.resizeWindow(WINDOW_TITLE,1024,576)

    tracker = MouseTracker() if mouse else CalibratedHandTracker()
    if mouse:cv2.setMouseCallback(WINDOW_TITLE,tracker.mouse_event)
    puzzle = Puzzle(grid_size)
    skin=Skin();performance=Performance()
    moves=0;round_kind='camera';cancelled_drags=0
    session_started=time.monotonic();camera_failures=0;last_shuffle=0
    evidence_saved=0.
    event('launch',input_mode='mouse' if mouse else 'live_camera',grid=grid_size)

    mode = "camera"

    # selection box
    sel_x1 = sel_y1 = sel_x2 = sel_y2 = None

    # states
    start_time = None
    end_time = None
    solved = False

    prev_pinch = False
    dragging = False
    drag_src_idx = None   # index of the tile being dragged

    # cursor position (pixel coords)
    cursor_x, cursor_y = 0, 0
    cursor_alpha = 0.35   # smoothing for non-pinch pointer

    # shuffle
    shuffling = False
    shuffle_start = 0


    # ================= LOOP =================
    while True:
        if mouse:
            ret=True;frame=np.full((720,1280,3),(32,26,19),np.uint8)
        else:
            ret,frame=cap.read()
            if not ret:
                camera_failures+=1
                if camera_failures>=15:
                    cap.release();cap=None;mouse=True
                    tracker.save()
                    if hasattr(tracker,'detector'):tracker.detector.close()
                    tracker=MouseTracker()
                    cv2.setMouseCallback(WINDOW_TITLE,tracker.mouse_event)
                    dragging=False;drag_src_idx=None;puzzle.selected=None;prev_pinch=False
                    event('camera_lost_fallback',vision_enabled=False)
                cv2.waitKey(30)
                continue
            camera_failures=0
            frame=cv2.flip(frame,1)
        clean_frame=frame.copy()
        output=frame

        tracker.find_hands(frame)
        tracker.draw_hands(frame)

        pinch, px, py = tracker.get_pinch()
        detected, ix, iy = tracker.get_index_pos()
        two_hands, p1, p2 = tracker.get_two_hand_indices()
        if dragging and (not detected or tracker.calibrating or tracker.require_release):
            dragging=False;drag_src_idx=None;puzzle.selected=None
            cancelled_drags+=1
            event('drag_cancelled',reason='tracking loss or controller not armed')

        h, w, _ = frame.shape

        render_tick=time.perf_counter()

        # ================= CAMERA MODE =================
        if mode == "camera":
            if two_hands:
                x1 = int(p1[0] * w)
                y1 = int(p1[1] * h)

                x2 = int(p2[0] * w)
                y2 = int(p2[1] * h)

                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)

                color = (254, 242, 0) # Cyan
                if pinch:
                    color = (127, 0, 255) # Hot Pink

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

                if pinch and not prev_pinch:
                    if abs(x2 - x1) > 100 and abs(y2 - y1) > 100:
                        sel_x1, sel_y1, sel_x2, sel_y2 = x1, y1, x2, y2
                        crop = clean_frame[sel_y1:sel_y2, sel_x1:sel_x2]

                        if crop.size != 0:
                            puzzle.create(crop)
                            shuffling = True
                            shuffle_start = time.time()
                            mode = "puzzle"
                            start_time = None
                            solved=False;end_time=None;moves=0;round_kind='camera'
                            event('round_start',source='live_camera_crop',input_mode='mouse' if mouse else 'live_camera')

            prev_pinch = pinch
            
            frame=skin.compose(frame,tracker=tracker,mouse=mouse,mode='camera',grid=grid_size,
                round_kind=round_kind,moves=moves,correct=0,start_time=start_time,end_time=end_time,
                solved=False,shuffling=shuffling,detected=detected,pinch=pinch,dragging=dragging,two_hands=two_hands)
            cv2.imshow(WINDOW_TITLE,frame)
            performance.capture(frame,'camera',tracker,mouse,round_kind,False)

        # ================= PUZZLE MODE =================
        else:
            output = frame.copy()

            # ===== CURSOR POSITION =====
            # During pinch: use the 1€-filtered pinch coords directly from tracker
            # Otherwise: smooth the index finger position for hover
            if prev_pinch and not pinch and detected:
                pass  # Drop at the last displayed pinch point; opening must not teleport the cursor.
            elif pinch and detected:
                cursor_x = int(px * w)
                cursor_y = int(py * h)
            elif detected:
                raw_cx = int(ix * w)
                raw_cy = int(iy * h)
                cursor_x = int(cursor_alpha * raw_cx + (1 - cursor_alpha) * cursor_x)
                cursor_y = int(cursor_alpha * raw_cy + (1 - cursor_alpha) * cursor_y)

            # Clamp only to frame. An out-of-board gesture must not select an edge tile.
            cursor_x=max(0,min(cursor_x,w-1));cursor_y=max(0,min(cursor_y,h-1))

            cursor_nx = cursor_x / w
            cursor_ny = cursor_y / h

            # ===== SHUFFLE =====
            if shuffling:
                if time.time() - shuffle_start < 1.8:
                    if time.time() - last_shuffle > 0.05:
                        i = random.randint(0, len(puzzle.tiles)-1)
                        j = random.randint(0, len(puzzle.tiles)-1)
                        puzzle.swap(i, j)
                        last_shuffle = time.time()
                else:
                    shuffling = False
                    start_time = time.time()

            # ===== INTERACTION =====
            if not shuffling and detected and not solved and not tracker.calibrating and not tracker.require_release:
                # --- PINCH START: grab a tile ---
                if pinch and not prev_pinch:
                    if inside_box(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h):
                        local = to_local(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h)
                        if local is not None:
                            lx, ly = local
                            idx = puzzle.get_index(lx, ly)
                            if idx is not None:
                                drag_src_idx = idx
                                puzzle.selected = idx
                                dragging = True

                # --- PINCH RELEASE: drop the tile ---
                elif not pinch and prev_pinch:
                    if dragging and drag_src_idx is not None:
                        local = to_local(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h)
                        if local is not None:
                            lx, ly = local
                            idx2 = puzzle.get_index(lx, ly)
                            if idx2 is not None:
                                puzzle.swap(drag_src_idx, idx2)
                                if drag_src_idx!=idx2:
                                    moves+=1
                                    event('swap',source_index=drag_src_idx,target_index=idx2,moves=moves,input_mode='mouse' if mouse else 'live_camera',personal_profile=bool(tracker.profile))

                        puzzle.selected = None
                        drag_src_idx = None
                        dragging = False

                        if not solved and puzzle.is_solved(puzzle.original_tiles):
                            solved = True
                            end_time = time.time()
                            event('solved',seconds=end_time-start_time,moves=moves,input_mode='mouse' if mouse else 'live_camera',round_kind=round_kind)

            prev_pinch = pinch

            if sel_x1 is not None:
                puzzle_img = puzzle.combine()
                puzzle_img = cv2.resize(puzzle_img, (sel_x2 - sel_x1, sel_y2 - sel_y1))
                output[sel_y1:sel_y2, sel_x1:sel_x2] = puzzle_img
                draw_grid(output, sel_x1, sel_y1, sel_x2, sel_y2,rows=grid_size,cols=grid_size)


            # ===== DRAW DRAG VISUALS =====
            gs = puzzle.grid_size
            cell_w = (sel_x2 - sel_x1) // gs
            cell_h = (sel_y2 - sel_y1) // gs

            # Highlight the drop-target cell when dragging
            if dragging and detected and sel_x1 is not None:
                local = to_local(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h)
                if local is not None:
                    lx, ly = local
                    hover_idx = puzzle.get_index(lx, ly)
                    if hover_idx is not None and hover_idx != drag_src_idx:
                        hr = hover_idx // gs
                        hc = hover_idx % gs
                        hx1 = sel_x1 + hc * cell_w
                        hy1 = sel_y1 + hr * cell_h
                        hx2 = hx1 + cell_w
                        hy2 = hy1 + cell_h
                        # Semi-transparent highlight on drop target
                        overlay = output.copy()
                        cv2.rectangle(overlay, (hx1, hy1), (hx2, hy2), (254, 242, 0), -1)
                        cv2.addWeighted(overlay, 0.25, output, 0.75, 0, output)
                        cv2.rectangle(output, (hx1, hy1), (hx2, hy2), MINT, 2)

            # Highlight the selected (source) tile
            if drag_src_idx is not None:
                sr = drag_src_idx // gs
                sc = drag_src_idx % gs
                sx1 = sel_x1 + sc * cell_w
                sy1 = sel_y1 + sr * cell_h
                sx2 = sx1 + cell_w
                sy2 = sy1 + cell_h
                cv2.rectangle(output, (sx1, sy1), (sx2, sy2), PEACH, 3)

                # Ghost tile preview following cursor
                tile_img = puzzle.tiles[drag_src_idx]
                ghost_w = cell_w // 2
                ghost_h = cell_h // 2
                ghost = cv2.resize(tile_img, (ghost_w, ghost_h))

                # Position ghost centered on cursor
                gx1 = cursor_x - ghost_w // 2
                gy1 = cursor_y - ghost_h // 2
                gx2 = gx1 + ghost_w
                gy2 = gy1 + ghost_h

                # Clamp to frame bounds
                src_x1 = max(0, -gx1)
                src_y1 = max(0, -gy1)
                dst_x1 = max(0, gx1)
                dst_y1 = max(0, gy1)
                dst_x2 = min(w, gx2)
                dst_y2 = min(h, gy2)
                src_x2 = src_x1 + (dst_x2 - dst_x1)
                src_y2 = src_y1 + (dst_y2 - dst_y1)

                if dst_x2 > dst_x1 and dst_y2 > dst_y1:
                    ghost_region = ghost[src_y1:src_y2, src_x1:src_x2]
                    frame_region = output[dst_y1:dst_y2, dst_x1:dst_x2]
                    blended = cv2.addWeighted(ghost_region, 0.7, frame_region, 0.3, 0)
                    output[dst_y1:dst_y2, dst_x1:dst_x2] = blended

            # ===== CURSOR =====
            if detected:
                if dragging:
                    # Pinching cursor: filled white + magenta ring
                    cv2.circle(output, (cursor_x, cursor_y), 10, PEACH, -1)
                    cv2.circle(output, (cursor_x, cursor_y), 12, (255, 255, 255), 2)
                else:
                    # Hover cursor: white dot + cyan ring
                    cv2.circle(output, (cursor_x, cursor_y), 7, (255, 255, 255), -1)
                    cv2.circle(output, (cursor_x, cursor_y), 9, MINT, 2)

            correct=sum(np.array_equal(a,b) for a,b in zip(puzzle.tiles,puzzle.original_tiles))
            output=skin.compose(output,tracker=tracker,mouse=mouse,mode='puzzle',grid=grid_size,
                round_kind=round_kind,moves=moves,correct=correct,start_time=start_time,end_time=end_time,
                solved=solved,shuffling=shuffling,detected=detected,pinch=pinch,dragging=dragging,
                two_hands=two_hands,board=(sel_x1,sel_y1,sel_x2,sel_y2))
            cv2.imshow(WINDOW_TITLE,output)
            performance.capture(output,'puzzle',tracker,mouse,round_kind,solved)

        performance.record((time.perf_counter()-render_tick)*1000,skin.last_ui_ms)
        key=cv2.waitKey(1)&0xFF
        tracker.handle_key(key)
        if key==27:
            break
        if key in (ord('r'),ord('R')):
            mode='camera';solved=False;dragging=False;drag_src_idx=None;puzzle.selected=None
            start_time=None;end_time=None;prev_pinch=False;tracker.require_release=not mouse
            event('reset')
        elif key in (ord('2'),ord('3')):
            if mode=='camera' and not tracker.calibrating:
                grid_size=int(chr(key));puzzle=Puzzle(grid_size)
                dragging=False;drag_src_idx=None;prev_pinch=False
                sel_x1=sel_y1=sel_x2=sel_y2=None
                start_time=None;end_time=None;solved=False;shuffling=False;moves=0
                tracker.require_release=not mouse
                if mouse:tracker.down=False
                event('difficulty_selected',grid=grid_size,input_mode='mouse' if mouse else 'live_camera')
            else:
                event('difficulty_ignored',grid=int(chr(key)),reason='calibration active' if tracker.calibrating else 'round active')
        elif key in (ord('n'),ord('N'),ord('d'),ord('D'),32):
            sel_x1,sel_y1,sel_x2,sel_y2=int(w*.2),int(h*.18),int(w*.8),int(h*.73)
            source=clean_frame[sel_y1:sel_y2,sel_x1:sel_x2].copy() if key==32 and not mouse else sample_board(grid_size)
            puzzle.create(source)
            demo=key in (ord('d'),ord('D'))
            if demo:
                puzzle.tiles=puzzle.original_tiles.copy();puzzle.swap(0,1)
            elif puzzle.is_solved(puzzle.original_tiles):puzzle.swap(0,1)
            mode='puzzle';round_kind='one-swap demo' if demo else ('camera' if key==32 and not mouse else 'shuffled sample')
            shuffling=False;solved=False;start_time=time.time();end_time=None;moves=0
            dragging=False;drag_src_idx=None;puzzle.selected=None;prev_pinch=False;tracker.require_release=not mouse
            event('round_start',source=round_kind,input_mode='mouse' if mouse else 'live_camera',grid=grid_size)
        limit=float(os.environ.get('AEROPUZZLE_MAX_SECONDS','0'))
        if limit and time.monotonic()-session_started>=limit:break
        if cv2.getWindowProperty(WINDOW_TITLE,cv2.WND_PROP_VISIBLE)<1:break
        if os.environ.get('AEROPUZZLE_EVIDENCE')=='1' and time.monotonic()-evidence_saved>2:
            cv2.imwrite(os.path.join(os.path.dirname(__file__),'..','..','results','adapted_frame_local.jpg'),frame if mode=='camera' else output)
            evidence_saved=time.monotonic()

    if cap is not None:cap.release()
    tracker.save()
    performance.save()
    if hasattr(tracker,'detector'):tracker.detector.close()
    event('exit',cancelled_drags=cancelled_drags,elapsed_s=time.monotonic()-session_started)
    cv2.destroyAllWindows()
