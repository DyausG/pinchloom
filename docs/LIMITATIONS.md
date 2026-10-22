# Limitations and future scope

- **Capture conditions:** low light, motion blur, occluded or sideways hands, a small palm and unstable handedness labels can interrupt interaction. Calibration checks finite geometry and scale; it does not explicitly score lighting, blur or pose quality.
- **Personal calibration:** the dataset is small, sequential and user-specific. Thresholds can change with posture and camera geometry. Handedness labels are not persistent identity. No multi-person identity management is implemented.
- **Performance:** the recorded complete vision loop was about 10 FPS on one local Windows setup. Nominal 30 ms confirmation is sampled at frame intervals. No controlled hardware comparison or motion-to-display latency benchmark exists.
- **Platform:** Windows x64 / Python 3.12.14 is validated. DirectShow capture is Windows-specific; other operating systems, ARM and other Python versions require separate validation.
- **Puzzle rules:** swaps are between arbitrary tile pairs. There is no empty-cell sliding mechanic, optimal solver or guaranteed difficulty distribution. Identical tile arrays can count as interchangeable; floor-based image splitting can discard residual edge pixels.
- **UI:** a nearly full-frame camera crop can suppress overlapping HUD panels. System font availability affects typography. R returns to the standard start layout.
- **Fallback:** mouse mode is explicitly CV OFF. A camera loss has a fallback path, but deliberate unplugging mid-round was not physically tested in the recorded live validation.
- **Evidence:** calibration fit, repeated same-image detections and callback regression wins do not establish independent recognition accuracy. There is no held-out gesture dataset, multi-user study or measured training improvement. Historical hardware model and detailed lighting settings were not recorded, so timing results should not be generalized.
- **Privacy:** normal operation writes local scalar telemetry, profiles and events. Opt-in developer capture flags can save camera pixels. Public screenshots cover camera-free sessions because existing live screenshots contain personal imagery.

Future work could evaluate diverse users and lighting, measure end-to-end latency with a controlled protocol, validate additional cameras/platforms, collect a consented held-out gesture test set, and capture a privacy-reviewed live gallery. These are proposals, not current features. Any controller or rendering changes would need fresh functional and webcam validation.
