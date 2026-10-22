# Features

## Gesture interaction

Local MediaPipe inference estimates landmarks for up to two hands. The controlling hand supplies an index hover point or a filtered thumb–index midpoint during a pinch. A pinch selects a source tile, movement shows a target and ghost preview, and release swaps the two tiles. Boundary checks reject out-of-board selection/drop. Tracking-loss cancellation and open-to-arm recovery protect pending interaction.

The personal calibration workflow prompts OPEN and PINCH poses, validates geometric samples and derives separate activation/release thresholds. Profiles are saved locally and loaded with L. X restores the active default controller without deleting the saved profile. Thresholds are personal measurements, not model training or gesture accuracy.

## Puzzle modes and sources

| Capability | Behavior |
|---|---|
| 2×2 Beginner | Four larger tiles, chosen with 2 before play |
| 3×3 Standard | Nine tiles, chosen with 3 before play; default launch size |
| Numbered sample | N creates a locally generated board with randomized tile order |
| One-swap practice | D exchanges only the first two original tiles; user interaction still has to solve it |
| Central camera capture | Space uses a clean crop spanning x=20–80%, y=18–73% of the current camera frame |
| Two-hand capture | Two index tips frame a region; a pinch captures if each dimension exceeds 100 px |
| Repeat play | N/D/Space start another round; R returns to start; victory remains visible |

The engine swaps arbitrary pairs. The two-hand capture route visibly shuffles for approximately 1.8 seconds; keyboard-created puzzles use immediate shuffling. Grid changes during a round or calibration are rejected until the user returns to the start screen.

## Afterglow Arcade interface

The native OpenCV window includes source/input/profile badges, contextual guidance, elapsed time, moves, correct-tile progress, source/target highlights and persistent completion feedback. States distinguish absent hands, lost tracking, open-to-arm, ready, pinching, grabbed and calibration. Sampling progress measures elapsed collection time; it does not show recognition confidence.

Text and font caches are bounded. HUD panels that intersect an unusually large captured board are hidden to preserve playable pixels; R restores the start layout. The native window scales the display, while board coordinates use the underlying image dimensions.

## Explicit fallback and local operation

`--mouse` disables vision and uses left-button dragging. An unavailable camera enters this same labeled fallback. No fake landmarks or CV results are shown in mouse mode; calibration and two-hand framing are unavailable, and Space uses a sample board.

All gameplay inference runs locally on the CPU using the bundled model. Runtime measurements and profiles are local ignored files. Windows is the tested platform. There is no account service, leaderboard, sound system, custom neural training, 4×4 mode or online multiplayer feature.
