# Controls

Focus **Pinchloom - Gesture Arcade** for keyboard input. Letter commands accept either case.

| Key | Action and conditions |
|---|---|
| 2 / 3 | Set Beginner 2×2 / Standard 3×3 on the start screen while calibration is inactive |
| C | Begin personal calibration in vision mode; show one hand clearly |
| O | Start three-second OPEN collection from `ready_open` |
| K | Start three-second PINCH collection from `ready_closed` |
| L | Load `results/personal_calibration.json`, if present; open that hand to arm |
| X | Cancel calibration and restore the default active controller; saved files remain |
| N | Start a new shuffled numbered puzzle |
| D | Start a labeled one-swap practice puzzle with tiles 1 and 2 exchanged |
| Space | Capture the central webcam region; sample board in mouse mode |
| R | Return to start and clear round/drag state; use before changing grid |
| Esc | Quit and release camera/model/window resources |

## Hand-controlled play

1. Use steady lighting and keep a palm facing the webcam. After calibration, loading, reset or tracking loss, **open the controlling hand** until the display is ready.
2. Hover over a tile with the index fingertip. Bring thumb and index together to grab.
3. Move the held tile over a second tile, then open the hand to release and swap. Opening retains the last pinch point for that drop.
4. Keep the hand visible. Lost control cancels a pending drag; open again before continuing. Dropping outside the board makes no swap.

At the camera start screen, two index fingertips can define opposite rectangle corners. Pinch with a region larger than 100 pixels on each axis to capture. Space offers a simpler central crop. Camera inputs are mirrored. The personal profile follows a MediaPipe handedness label; use the same hand and do not assume persistent identity across people.

## Mouse fallback

Launch `python run.py --mouse` from the configured environment. Choose 2/3, then N or D. Hold the left button on a source tile, move and release over a target. Badges explicitly display **MOUSE · CV OFF** and **FALLBACK INPUT**. Calibration keys have no effect in this mode. Camera-free mode does not need or pretend to run the hand model.

For a reliable short demonstration: choose 2, press D, and swap the two top tiles. N and camera captures provide unrestricted rounds afterward. The preset still requires a real swap; it does not automatically win.
