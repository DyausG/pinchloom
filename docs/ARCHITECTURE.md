# Architecture

Pinchloom is a single-process Windows desktop application. Camera acquisition, inference, interaction, puzzle updates and rendering run in sequence; no cloud service or training pipeline participates.

## Components and interfaces

| File under `aeropuzzle_game/aeropuzzle/` | Responsibility and interface |
|---|---|
| `main.py` | CLI: `--mouse`, `--grid {2,3}`, `--camera INDEX`; calls `app.main` |
| `app.py` | Camera/window ownership, game states, crop selection, drag transitions, rendering and keys |
| `hand_tracking.py` | `HandTracker`: MediaPipe Tasks model, landmark drawing, pinch geometry, hysteresis and midpoint filtering |
| `calibration.py` | `CalibratedHandTracker`: selected hand, pixel-correct ratio, prompted sampling, threshold persistence and release-to-arm safety |
| `maze.py` | `Puzzle`: splits an image, shuffles, swaps, combines and compares tiles |
| `support.py` | Generated numbered images, event records and `MouseTracker` with the same interaction interface |
| `ui_skin.py` | `Skin.compose`: Afterglow interface, truthful input states and bounded text caches |
| `performance.py` | Bounded timing samples, local summaries and opt-in validation captures |
| `assets/hand_landmarker.task` | Bundled pretrained model, resolved through `importlib.resources` |

`run.py` anchors paths to the clone, sets the local Matplotlib cache, inserts `aeropuzzle_game` on the import path and installs a process-local socket guard before entering the CLI. Retaining the package layout preserves imports and model resolution. Run this launcher rather than installing an unrelated PyPI package.

## Frame and control flow

1. Open DirectShow camera input, normally request 1280×720, and create a resizable 1024×576 display window. Explicit mouse mode omits camera/model construction.
2. Mirror a camera frame and retain a clean copy before hand overlays. Infer on a proportionally resized copy at at most 640 px width. BGR pixels become RGB for MediaPipe. Options permit two hands with detection/presence/tracking thresholds of 0.5. The task remains in default synchronous IMAGE mode.
3. Resolve a controlling hand: a calibration-selected label, a loaded profile's label, or the largest normalized palm scale when neither exists. The default base tracker evaluates up to two pinches; the personalized path restricts activation to the profile label.
4. Update gesture state, obtain the pointer and two-hand framing positions, and cancel a drag when the controller loses a valid point, enters calibration or requires rearming.
5. In start/camera mode, allow grid selection, samples, central capture or a two-fingertip rectangle. In puzzle mode, map a pinch edge to a source tile and the release edge to a target.
6. Update puzzle state, compose image tiles and feedback, then compose the UI and submit the frame. Read the next key and repeat.

## State management

The game uses `camera` and `puzzle` modes with shuffle, solved, drag, timing and source/target state. Calibration uses `idle → ready_open → open → ready_closed → closed → idle`; a failed fit returns to `ready_open`. Pinch activation has temporal confirmation and separate release thresholds. After loss, reset, loading or successful calibration, an open controlling hand must rearm. Returning with an already closed hand cannot immediately grab a new tile.

Grid changes are accepted only at the start screen while calibration is inactive. N/D/Space create new rounds; R returns to the start. Victory remains displayed until another user action. Two-hand region capture uses a short animated shuffle; keyboard-created boards are shuffled immediately. See [controls](CONTROLS.md).

## Local storage and privacy

`results/` holds local calibration JSON, scalar samples, tracking telemetry and JSONL game events. `results/pinchloom_latest/` normally holds performance summaries. These are generated at runtime and ignored by Git. `PINCHLOOM_RUN_DIR` redirects performance output only; it does not redirect all calibration/events. Do not use it as a privacy sandbox for the whole app.

Ordinary launch does not save webcam images. Developer flags `AEROPUZZLE_EVIDENCE=1` and `PINCHLOOM_CAPTURE=1` enable local image capture; keep them unset for normal use. The repository contains only the intentionally reviewed public scalar sample and two camera-free screenshot assets.

After 15 consecutive camera-read failures, the loop releases the camera/model, cancels pending interaction and switches to mouse fallback. Startup with an unavailable camera also enters fallback. Exit closes the model, releases capture and destroys windows. Deliberate physical unplugging was not part of recorded live validation.
