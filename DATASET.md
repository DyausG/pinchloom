# Pinchloom OPEN/PINCH Calibration Measurements

**Dataset name for the submission form:** `Pinchloom OPEN/PINCH Calibration Measurements`

**Dataset documentation link:** [https://github.com/DyausG/pinchloom/blob/main/DATASET.md](https://github.com/DyausG/pinchloom/blob/main/DATASET.md)

**Numerical data:** [data/calibration_measurements.csv](data/calibration_measurements.csv) · [metadata](data/metadata.json)

## Purpose and provenance

Pinchloom uses Google's pretrained MediaPipe Hand Landmarker and locally collected, prompted OPEN/PINCH measurements to personalize a geometric controller. It trains no custom neural network. This public sample contains **62 real scalar ratios, 31 OPEN and 31 PINCH**, from the completed application's recorded local validation. Values were exported without alteration from the existing validated sample record; no synthetic measurements were added.

This is a small calibration sample from one session, not a broadly representative gesture-recognition dataset. The public export removes personal profiles, handedness, timestamps, file-system paths and raw imagery. Rows preserve collection order within each pose but have no cross-session subject identifier. The export is shared under the repository's [MIT license](LICENSE).

## Collection and schema

The user presses C, displays one open hand and presses O to collect valid measurements for three seconds; then touches thumb and index and presses K for a three-second PINCH phase. The calibration tracker selects a handedness label and appends one valid ratio per processed frame. The local JSON calls the categories `open` and `closed`; the public CSV names them **OPEN** and **PINCH**.

| Column | Type | Meaning |
|---|---|---|
| `pose` | OPEN or PINCH | Prompted pose, not independently annotated ground truth |
| `ratio` | Dimensionless float | Pixel-correct thumb–index distance divided by wrist–middle-MCP distance |

The four relevant landmarks are **0 wrist**, **4 thumb tip**, **8 index tip**, **9 middle MCP**. For normalized image coordinates:

$$d_{ij}=sqrt{[W(x_i-x_j)]^2+[H(y_i-y_j)]^2},qquad r=d_{4,8}/d_{0,9}.$$

The palm denominator reduces hand-size/distance effects. Width/height multiplication corrects pixel aspect. The controller ignores z. A sample requires finite x/y coordinates for all returned landmarks, a palm baseline of at least **25 original-frame pixels**, and $0le rle4$. These are implementation checks, not a claim of comprehensive pose or image-quality validation.

## Quantiles, thresholds and use

A fit requires **at least 25 valid values per category**. With NumPy's default percentile calculation:

$$a=Q_{10}(OPEN),quad b=Q_{90}(PINCH),quad g=a-b.$$

Reject if $g<0.08$. Otherwise use $T_{close}=b+0.35g$ and $T_{release}=b+0.65g$. Smaller ratios engage a pinch; larger ratios release it, with hysteresis and temporal confirmation. [Full methodology](docs/METHODOLOGY.md).

`data/metadata.json` records the computed sample quantiles/thresholds and source-record SHA-256. The public CSV supports reproducing the fit through `scripts/verify_release.py`. It does **not** load automatically at runtime and should not be installed as another user's personal profile. Recalibrate for your own hand and environment.

## Relationship to MediaPipe data

The sample is downstream geometric calibration data, not Google's neural training dataset. The pretrained model and its training/evaluation descriptions are provided by Google: [Hand Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker), [model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20%28Lite_Full%29%20with%20Fairness%20Oct%202021.pdf). No Google training images are redistributed here. Do not cite an unrelated gesture-image corpus as the dataset used to train Pinchloom.

## Limits and privacy

Consecutive samples are correlated; class labels reflect prompted poses and are not independent expert annotations. Quantile separation measures fit on those same samples, not classification accuracy. There is no held-out split, subject diversity study or evidence that these thresholds generalize. The scalar sample cannot independently verify landmark quality because images and complete landmarks are excluded.

Personal runtime profiles, telemetry and webcam images remain local under ignored `results/`. Share only reviewed exports; keep developer image-capture flags unset during ordinary use. Numerical de-identification reduces exposure but is not a formal anonymity guarantee.

## Suggested citation

DyausG. (2026). *Pinchloom OPEN/PINCH Calibration Measurements* [Numerical calibration sample and documentation]. Pinchloom. https://github.com/DyausG/pinchloom/blob/main/DATASET.md. For an immutable citation, replace `main` with the repository commit used for evaluation.
