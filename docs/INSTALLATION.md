# Installation and troubleshooting

## Supported environment

The validated platform is **Windows x64 with CPython 3.12.14**. Use Python 3.12 x64, Git, a desktop session, and a webcam for hand control. Mouse fallback works without a camera. Other Python releases, ARM builds, Linux and macOS are not validated; the camera backend is Windows DirectShow.

Install Python and Git from their official distributors. Confirm `py -3.12 --version` and `git --version` in PowerShell. Close other applications using the webcam and allow desktop camera access in Windows Settings.

## Clone, install and launch

```powershell
git clone https://github.com/DyausG/pinchloom.git
cd pinchloom
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe run.py
```

Activation and PowerShell execution-policy changes are unnecessary when invoking the environment's Python directly. `requirements.txt` and `requirements-resolved.txt` contain the identical 19 pinned versions from the validated environment. Main packages are MediaPipe 0.10.32, opencv-contrib-python 4.10.0.84, NumPy 2.2.6 and Pillow 12.3.0. Avoid mixing multiple OpenCV wheel variants in this environment.

```powershell
.\.venv\Scripts\python.exe run.py --mouse
.\.venv\Scripts\python.exe run.py --grid 2
.\.venv\Scripts\python.exe run.py --camera 1
.\.venv\Scripts\python.exe run.py --help
.\.venv\Scripts\python.exe scripts/verify_release.py
```

The verification runner executes two headless integration suites plus geometry/controller/dataset/model checks. Headless integration stubs camera/window calls and uses scripted input; it is not a webcam validation run. Outputs are written to ignored `results/`. Test commands can overwrite that clone's local telemetry; run in a separate clone if you need to preserve runtime results.

## Model and assets

The pretrained task file is included at `aeropuzzle_game/aeropuzzle/assets/hand_landmarker.task`, preserving the resource path. No separately downloaded artwork or fonts are required. The app renders numbered puzzle images locally.

If the model is missing or damaged, restore it from Git. Alternatively retrieve the exact official [version 1 model](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task) and verify the expected SHA-256 before running:

```powershell
Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task' -OutFile 'aeropuzzle_game/aeropuzzle/assets/hand_landmarker.task'
Get-FileHash -Algorithm SHA256 'aeropuzzle_game/aeropuzzle/assets/hand_landmarker.task'
```

Expected: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`, **7,819,105 bytes**. Review [attribution and Apache-2.0 terms](../ATTRIBUTION.md). Installation downloads require network access; ordinary play uses local inference through `run.py`'s process-local external-socket guard.

## First use and local data

The release intentionally includes no personal profile. Start with the default controller or press C→O→K to create your own. Each pose takes three seconds and needs at least 25 valid samples. Keep one palm clearly visible. After fitting, open the hand to arm. On a later launch press L to load your saved profile; it is not loaded automatically. The sample CSV is documentation data, not a universal profile.

`results/` and `cache/` are created locally and excluded from Git. Keep `AEROPUZZLE_EVIDENCE` and `PINCHLOOM_CAPTURE` unset during ordinary use: those opt-in validation flags can save camera images.

## Troubleshooting

| Symptom | Check |
|---|---|
| `py -3.12` unavailable | Install/register Python 3.12 x64 or use its full executable path to create the venv |
| Package has no matching distribution | Confirm Python 3.12 x64 and the pinned requirements; do not silently change validated versions |
| Camera unavailable / CV OFF | Allow desktop camera access, close competing apps, try `--camera 1`; use `--mouse` for camera-free play |
| Model cannot load | Verify the asset exists, its size/hash and the exact environment; launch through root `run.py` |
| No valid hand / controller won't arm | Show the correct open palm, move closer, improve lighting, reduce occlusion; load or recalibrate as needed |
| Fewer than 25 samples / overlapping poses | Hold each pose steady for its full phase; separate thumb/index clearly for OPEN and touch for PINCH |
| Grid key ignored | Press R, finish/cancel calibration, then choose 2 or 3 |
| HUD panels missing on large photo | The UI hides panels that cover the board; R returns to start |
| UI text differs across systems | Windows fonts are used when available; fallback fonts may change appearance |

Do not report model accuracy from a successful calibration or a mouse-only session. See [validation scope](VALIDATION.md) and [limits](LIMITATIONS.md).
