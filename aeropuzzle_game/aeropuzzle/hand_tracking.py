import cv2
import math
import time
from importlib.resources import files

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8), # Index
    (5, 9), (9, 10), (10, 11), (11, 12), # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17) # Pinky & palm
]


def _hand_scale(hand):
    """Estimate hand scale from wrist (0) to middle finger MCP (9).
    Returns a baseline distance used for adaptive pinch thresholds."""
    dx = hand[9].x - hand[0].x
    dy = hand[9].y - hand[0].y
    return math.sqrt(dx * dx + dy * dy)


def _get_model_path():
    """Resolve the path to the hand_landmarker.task model file
    using importlib.resources so it works after pip install."""
    model_ref = files("aeropuzzle.assets").joinpath("hand_landmarker.task")
    # as_posix() works for mediapipe on all platforms; if the resource
    # is inside a zip/wheel, importlib extracts it to a temp path.
    return str(model_ref)


class HandTracker:
    def __init__(self):
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        model_path = _get_model_path()

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.results = None

        # Per-hand pinch state tracked by handedness ("Left", "Right")
        self._pinch_state = {"Left": False, "Right": False}
        self._pinch_start_time = {"Left": 0.0, "Right": 0.0}

        # Minimum time (seconds) a pinch must stay closed before it's
        # acknowledged — prevents accidental flicker.
        self.PINCH_CONFIRM_DELAY = 0.03  # 30 ms (faster engagement)

        # Adaptive threshold multipliers relative to hand scale
        self.PINCH_CLOSE_RATIO = 0.22   # easier to START pinch
        self.PINCH_OPEN_RATIO  = 0.35   # easier to HOLD pinch

        # ---- Velocity-adaptive 1€-style position filter ----
        self._pinch_px = 0.0
        self._pinch_py = 0.0
        self._prev_raw_x = 0.0
        self._prev_raw_y = 0.0
        self._pinch_pos_inited = False
        self._prev_time = 0.0
        # 1€ filter tuning
        self._min_cutoff = 1.5   # low = smoother when still (increased for snappiness)
        self._beta = 5.0         # high = more responsive to fast moves (increased for less drag lag)
        self._d_cutoff = 1.0     # derivative filter cutoff

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def find_hands(self, frame):
        import mediapipe as mp
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        self.results = self.detector.detect(mp_image)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw_hands(self, frame):
        if self.results and self.results.hand_landmarks:
            h, w, _ = frame.shape
            for hand_landmarks in self.results.hand_landmarks:
                for connection in HAND_CONNECTIONS:
                    p1 = hand_landmarks[connection[0]]
                    p2 = hand_landmarks[connection[1]]
                    cv2.line(frame,
                             (int(p1.x * w), int(p1.y * h)),
                             (int(p2.x * w), int(p2.y * h)),
                             (220, 220, 220), 1)
                for lm in hand_landmarks:
                    cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, (160, 245, 0), -1)

    # ------------------------------------------------------------------
    # Pinch detection — adaptive, per-hand, with hysteresis + debounce
    # ------------------------------------------------------------------
    def _update_pinch_for_hand(self, hand, idx):
        """Update pinch state for a single hand (idx 0 or 1).
        Returns (is_pinching, midpoint_x, midpoint_y)."""
        thumb_x, thumb_y = hand[4].x, hand[4].y
        index_x, index_y = hand[8].x, hand[8].y

        dist = math.sqrt((index_x - thumb_x) ** 2 + (index_y - thumb_y) ** 2)
        scale = max(_hand_scale(hand), 0.01)  # avoid division by zero
        ratio = dist / scale

        # Resolve handedness label ("Left" or "Right")
        label = "Right"
        try:
            if self.results and hasattr(self.results, "handedness") and len(self.results.handedness) > idx:
                label = self.results.handedness[idx][0].category_name
        except Exception:
            pass

        if label not in self._pinch_state:
            self._pinch_state[label] = False
            self._pinch_start_time[label] = 0.0

        now = time.time()

        if self._pinch_state[label]:
            # Currently pinching — open only when ratio exceeds the OPEN threshold
            # and absolute distance is not in hold range
            is_hold = (ratio <= self.PINCH_OPEN_RATIO) or (scale > 0.08 and dist < 0.06)
            if not is_hold:
                self._pinch_state[label] = False
        else:
            # Not pinching — close when ratio drops below CLOSE threshold or absolute distance is small
            is_close = (ratio < self.PINCH_CLOSE_RATIO) or (scale > 0.08 and dist < 0.04)
            if is_close:
                if self._pinch_start_time[label] == 0.0:
                    self._pinch_start_time[label] = now
                elif now - self._pinch_start_time[label] >= self.PINCH_CONFIRM_DELAY:
                    self._pinch_state[label] = True
            else:
                self._pinch_start_time[label] = 0.0

        # Use midpoint of thumb + index for a stable pinch position
        mx = (thumb_x + index_x) / 2.0
        my = (thumb_y + index_y) / 2.0
        return self._pinch_state[label], mx, my

    def _one_euro_alpha(self, cutoff, dt):
        """Compute the smoothing factor for a given cutoff frequency."""
        if dt <= 0:
            return 1.0
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def _smooth_position(self, raw_x, raw_y):
        """Apply velocity-adaptive 1€ filter to the pinch position.
        Fast hand movement → minimal smoothing (responsive).
        Slow/still hand → heavy smoothing (stable, no jitter)."""
        now = time.time()

        if not self._pinch_pos_inited:
            # First sample — seed with raw position, no smoothing
            self._pinch_px = raw_x
            self._pinch_py = raw_y
            self._prev_raw_x = raw_x
            self._prev_raw_y = raw_y
            self._prev_time = now
            self._pinch_pos_inited = True
            return raw_x, raw_y

        dt = now - self._prev_time
        if dt <= 0:
            dt = 1.0 / 30.0  # assume ~30 fps
        self._prev_time = now

        # Estimate velocity (derivative)
        dx = (raw_x - self._prev_raw_x) / dt
        dy = (raw_y - self._prev_raw_y) / dt
        self._prev_raw_x = raw_x
        self._prev_raw_y = raw_y

        speed = math.sqrt(dx * dx + dy * dy)

        # Adaptive cutoff: higher speed → higher cutoff → less smoothing
        cutoff = self._min_cutoff + self._beta * speed
        alpha = self._one_euro_alpha(cutoff, dt)

        self._pinch_px = alpha * raw_x + (1.0 - alpha) * self._pinch_px
        self._pinch_py = alpha * raw_y + (1.0 - alpha) * self._pinch_py

        return self._pinch_px, self._pinch_py

    def get_pinch(self):
        """Return (is_pinching, x, y) for the first hand that is pinching.
        Position is smoothed using a velocity-adaptive 1€ filter."""
        if self.results and self.results.hand_landmarks:
            # Reset state for hands that disappeared
            present_labels = []
            for i in range(len(self.results.hand_landmarks[:2])):
                try:
                    if self.results.handedness and len(self.results.handedness) > i:
                        present_labels.append(self.results.handedness[i][0].category_name)
                except Exception:
                    pass
            for label in ["Left", "Right"]:
                if label not in present_labels:
                    self._pinch_state[label] = False
                    self._pinch_start_time[label] = 0.0

            # Check each hand
            for i, hand in enumerate(self.results.hand_landmarks[:2]):
                pinching, mx, my = self._update_pinch_for_hand(hand, i)
                if pinching:
                    sx, sy = self._smooth_position(mx, my)
                    return True, sx, sy

            # No hand is pinching — reset filter so next pinch starts fresh
            self._pinch_pos_inited = False
            hand = self.results.hand_landmarks[0]
            return False, hand[8].x, hand[8].y

        # No hands detected at all
        self._pinch_pos_inited = False
        for label in ["Left", "Right"]:
            self._pinch_state[label] = False
            self._pinch_start_time[label] = 0.0
        return False, 0, 0

    # ------------------------------------------------------------------
    # Two-hand helpers (unchanged)
    # ------------------------------------------------------------------
    def get_two_hand_indices(self):
        points = []
        if self.results and self.results.hand_landmarks:
            for hand in self.results.hand_landmarks:
                points.append((hand[8].x, hand[8].y))
        if len(points) >= 2:
            return True, points[0], points[1]
        return False, (0, 0), (0, 0)

    def get_index_pos(self):
        if self.results and self.results.hand_landmarks:
            hand = self.results.hand_landmarks[0]
            return True, hand[8].x, hand[8].y
        return False, 0, 0
