# Validation and measured results

Pinchloom separates real camera operation, saved-image model inference, scripted app-loop regressions and publication checks. A calibration fit or callback win is not an independent recognition-accuracy measurement.

## Recorded live validation — 14 October 2026

These results are transcribed from the completed application's local acceptance records. [Sanitized numerical evidence](evidence/recorded_validation.json) retains measured performance, actual win events and test outcomes without personal profile JSON, local paths or camera pixels. Human confirmations below come from the recorded acceptance report; no new human webcam session is claimed during publication.

| Check | Recorded outcome and scope |
|---|---|
| Hand-controlled Beginner win | One actual calibrated swap, **2.900 s**, 2×2 preset |
| Hand-controlled Standard win | One actual calibrated swap, **9.609 s**, 3×3 preset |
| Grid selection | Human 2→3→2 selection and subsequent rounds at both sizes |
| Fresh calibration | **30 OPEN + 30 PINCH** values; close/release approximately **0.417/0.645**, separation **0.760** in that session |
| Recovery | Human confirmed live recovery and losses were logged; the specific drag-cancellation event is established by scripted app-loop checks, not a distinct recorded human drag-cancel event |
| Actual mouse fallback | Human desktop one-swap win, **0.935 s**, with CV OFF |
| Camera unavailable | Actual invalid-device `--camera 99` launch rendered fallback and exited normally |
| Final normal camera restart | **652 frames in 65.358 s**, control points in **259 frames**, **45 pinching frames**, no screenshot capture; exit code 0 |

Win times are user round-completion durations, not model inference or motion-to-display latency. The fresh 30/30 calibration above differs from the older **31/31** genuine sample published in [DATASET.md](../DATASET.md); they are separate recorded sessions, not conflicting counts. The original personal profiles are not distributed.

## Measured performance

| Session | Scope | Full-loop FPS | UI compose p50 / p95 | Update + render p50 / p95 |
|---|---|---:|---:|---:|
| Final normal, 65.36 s | Real webcam/model, mixed hands/no hands, screenshot capture off | 9.98 | 6.67 / 12.48 ms | 7.21 / 13.06 ms |
| Longer live session, 672.66 s | Real wins/calibration plus periodic local PNG capture | 10.02 | 8.65 / 16.97 ms | 9.43 / 21.36 ms |
| Human mouse session, 37.93 s | CV OFF, no model, actual mouse win | 57.82 | 4.71 / 11.88 ms | 5.58 / 13.91 ms |

Full-loop FPS includes capture, inference, rendering and input wait. Update/render excludes capture/inference/waitKey and includes game/window work; capture-enabled sessions also include evidence work. UI timing measures composition only. Timing buffers retain at most the latest 1,800 samples, while FPS spans the session. These observations used one local Windows environment; hardware model and detailed lighting parameters were not preserved in the available report. They do not establish general performance, a controlled speedup or hand-recognition accuracy. Mouse FPS is not an inference benchmark.

## Recorded saved-image inference

A separate fresh model process detected hand landmarks in **20/20 repeated runs on the same saved real camera image**, with p50/p95 approximately **40.20/58.30 ms**. It ran while another camera process was active. The launcher blocked external Python socket connections in that process; Windows networking itself was not disabled.

This is offline file inference, not fresh webcam gameplay, 20 independent trials or a labeled accuracy benchmark. The personal input image is excluded, so the public repository cannot reproduce that exact image-dependent detection result. The release provides a public blank-image real-model smoke check instead, clearly labeled below.

## Reproducible publication checks — 22 October 2026

From the repository root in the configured environment:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe run.py --help
.\.venv\Scripts\python.exe scripts/verify_release.py
```

The runner executes:

- **Five game regression groups:** threshold fit/rejection; both grid mechanics; repeated callback wins; out-of-board rejection; lost-control drag cancellation.
- **Four interface/difficulty groups:** selection and active-round guards; calibration guard; clean camera-crop geometry at both grids; truthful states and playable-board non-occlusion at 1280×720, 960×540, 640×480 and a near-full-frame crop.
- **Eight release checks:** preserved application hashes; aspect/resolution-correct geometry; invalid-measurement rejection; calibration rejection; personalized hysteresis; release-to-arm/loss; actual public dataset fit; official model integrity, load and inference on blank pixels.

Camera/window APIs and interaction inputs are stubbed in the integration suites. Their camera-crop checks use synthetic fixture pixels and their wins use callbacks. The model smoke check runs the actual MediaPipe Tasks detector on a blank 640×480 image and expects zero hands; it verifies execution, not positive hand detection or accuracy. It does not open a webcam or a native window.

The only portability edit to the existing suites removes `test_pinchloom.py`'s dependency on a private absolute acceptance-directory pointer and writes under ignored `results/scripted/`. Application source, launcher, model, original package license and original dependency manifest remain byte-identical to the local validated project. [Preserved-file hashes](evidence/preserved_files.json) and [model provenance](evidence/model_provenance.json) make those checks reproducible. [Publication check record](evidence/publication_checks.json) records completed checks and their scope.

## Evidence and coverage limits

The public gallery contains only two genuine camera-free human-session frames. Existing live main/tracking/calibration/photo/victory screenshots contain identifiable personal imagery and are excluded, with no fabricated replacements. Live unplugging, multi-user generalization, independent gesture accuracy and controlled end-to-end latency remain untested. [Gallery provenance](../screenshots/README.md) · [Limitations](LIMITATIONS.md).
