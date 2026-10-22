# Methodology

Pinchloom combines pretrained landmark inference with deterministic gesture geometry. Personalized calibration estimates thresholds; it does not fit neural weights or a learned gesture classifier.

## Landmarks and feature geometry

MediaPipe returns 21 image-space landmarks and handedness per detected hand. Four landmarks define the personal feature: **0 wrist**, **4 thumb tip**, **8 index tip**, **9 middle-finger MCP**. For normalized coordinates and original frame dimensions $W,H$:

$$d_{ij}=sqrt{[W(x_i-x_j)]^2+[H(y_i-y_j)]^2}, qquad r=d_{4,8}/d_{0,9}.$$

The ratio normalizes thumb–index separation by palm scale. Multiplying axes by frame dimensions avoids treating normalized x and y units as equal pixel distances on a rectangular image. The personal validity check requires a palm baseline of at least **25 original-frame pixels**, finite x/y values for all landmarks, and a finite ratio in **[0,4]**. The image-space z coordinate is not used. No blur, lighting, pose-angle or landmark-confidence rejection is implemented beyond MediaPipe's own options and these checks.

Inference receives at most 640 px width; normalized outputs are evaluated using the original frame's dimensions. Uniform rescaling preserves the ratio, while the 25 px check intentionally refers to the original frame.

## Prompted calibration

Press C, hold one clear open palm with separated thumb/index, then O. Valid ratios are collected over three seconds. Next touch thumb and index and press K for a three-second PINCH phase. The selected handedness label is retained. The sampler appends one valid ratio per processed frame; samples are temporally correlated. If either category has fewer than 25 measurements, retry with a steady visible hand.

Let $a=Q_{10}(OPEN)$, $b=Q_{90}(PINCH)$ and $g=a-b$. NumPy's default percentile interpolation is used. A fit is rejected when $g<0.08$; equality is accepted. Otherwise:

$$T_{close}=b+0.35g,qquad T_{release}=b+0.65g.$$

These thresholds lie inside the measured separation. The profile stores thresholds, quantiles, counts and handedness locally. It is saved after successful calibration but **not automatically loaded on the next launch**: use L. X clears the active profile and restores defaults; it does not delete saved files. The public numerical sample is never automatically loaded into the controller.

## Pinch state and temporal behavior

For the personal controller, an inactive pinch engages when $r<T_{close}$ and the confirmation timer passes its nominal **0.03 s** delay. An active pinch releases when $r>T_{release}$. Equality leaves the corresponding state unchanged. Since inference is frame-based, 30 ms is a configured minimum, not a guarantee of 30 ms response at the observed roughly 10 FPS. In the implementation, the confirmation timestamp resets on a non-close sample while inactive; it is not a separate accuracy/confidence measure.

The default controller uses normalized-coordinate distances without pixel aspect correction. Its relative close/open multipliers are **0.22/0.35**, plus absolute close/hold alternatives **0.04/0.06** when normalized palm scale exceeds **0.08**. Do not apply calibrated pixel ratios to those default constants as though they were the same metric. Release-to-arm uses the active profile's release threshold, or **0.6** on the pixel-correct ratio in default mode.

The thumb–index midpoint is smoothed during a pinch. A velocity-adaptive, 1€-style filter uses:

$$f_c=1.5+5v,quad 	au=(2pi f_c)^{-1},quad alpha=(1+	au/Delta t)^{-1},quad hat p_t=alpha p_t+(1-alpha)hat p_{t-1}.$$

Here $v$ is the norm of the raw normalized-coordinate velocity. This is the actual simplified filter; it does not separately low-pass the derivative. Hover uses an exponential blend of **0.35 new / 0.65 previous**. On the release frame, the cursor retains its last displayed pinch point to avoid a jump to the opening index fingertip.

## Recovery and mapping

Absent/invalid control points suppress interaction. Loss of a suitable hand or ratio requires an open hand to rearm; the app cancels a pending drag. Handedness identity is label-based, not biometric identity or persistent multi-person tracking.

For frame pointer $(p_x,p_y)$ in normalized coordinates and board rectangle $(x_1,y_1,x_2,y_2)$:

$$u=(Wp_x-x_1)/(x_2-x_1), qquad v=(Hp_y-y_1)/(y_2-y_1).$$

Coordinates outside the board are rejected before tile selection. For grid size $n$:

$$column=min(lfloor nu
floor,n-1),quad row=min(lfloor nv
floor,n-1),quad index=n,row+column.$$

The minimum operation keeps the exact right/bottom boundary in the final cell. A drag starts on a pinch edge and releases onto a valid target. Releasing outside the board makes no swap. Tile references exchange places; distinct-index swaps increment the move count. Exact per-position NumPy array equality against the captured original tiles establishes completion. Identical-looking tile arrays can therefore be interchangeable. Image dimensions are floor-divided by the grid size, so residual edge pixels may be dropped.

This is an arbitrary tile-swap puzzle, with no blank cell or sliding-puzzle parity constraint. [Dataset details](../DATASET.md) · [Architecture](ARCHITECTURE.md).
