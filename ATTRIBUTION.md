# Attribution and third-party notices

Pinchloom distributes application code under the [MIT license](LICENSE). The pretrained model has its own Apache-2.0 terms. These notices identify the origin of components; the product documentation describes the application itself.

## AeroPuzzle

- Author: Aarthi Suresh / **Aarthirt14**.
- Source: [AeroPuzzle](https://github.com/Aarthirt14/AeroPuzzle).
- Source revision recorded with the local project: `03a8376eb7e4f9f3d0a2365055eb3898569f38c8`.
- License: MIT, **Copyright (c) 2025 Aarthirt14**. The complete notice is retained in [aeropuzzle_game/LICENSE](aeropuzzle_game/LICENSE), [THIRD_PARTY_LICENSES/AeroPuzzle-MIT.txt](THIRD_PARTY_LICENSES/AeroPuzzle-MIT.txt), and the root license.

The `aeropuzzle` Python namespace is retained so imports and resource paths continue to work. AeroPuzzle supplies the picture-tile puzzle mechanics, hand-tracking controller and portions of the camera/game loop. The published application also includes personal calibration, interaction recovery, sample-board/mouse helpers, the Afterglow display layer, timing instrumentation and launch integration. Those descriptions identify source boundaries without claiming independent invention of third-party code. Existing source comments, CLI descriptions and the in-window acknowledgment are preserved.

## Google MediaPipe and pretrained model

MediaPipe is developed by Google and contributors: [source](https://github.com/google-ai-edge/mediapipe), [Hand Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker). Its Apache-2.0 text is included at [THIRD_PARTY_LICENSES/MediaPipe-Apache-2.0.txt](THIRD_PARTY_LICENSES/MediaPipe-Apache-2.0.txt).

The unmodified `aeropuzzle_game/aeropuzzle/assets/hand_landmarker.task` contains Google's pretrained palm detector and hand-landmark models. The official guide links the [Hand Tracking model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20%28Lite_Full%29%20with%20Fairness%20Oct%202021.pdf), whose detector specifications identify **Apache License, Version 2.0**. The task bundle was compared byte for byte with Google's [version 1 float16 download](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task) on 22 October 2026:

```text
Size:   7,819,105 bytes
SHA256: fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1
```

The model is supplied under Apache-2.0, separately from the application's MIT license. No model weights were changed. Pinchloom does not train or fine-tune a neural network and does not redistribute Google's training dataset.

## Installed dependencies and assets

OpenCV, NumPy and Pillow supply camera/image operations, numerical arrays and typography. MediaPipe also installs supporting packages listed in `requirements.txt`. They are installed from their distributors; their package and bundled-component license notices remain with those distributions. OpenCV's wheels can include additional third-party notices: the application's MIT license does not replace them. No Python environment or dependency binaries are repackaged here.

Numbered puzzle boards are rendered by `sample_board`; no downloaded puzzle artwork is included. No Microsoft font files are distributed: the UI uses fonts available on the local system, falling back to Pillow's default font. The two published screenshots are genuine application frames with vision disabled. Private camera imagery and personal profile files are excluded. The small numerical calibration sample is documented in [DATASET.md](DATASET.md) and shared under the repository's MIT terms.
