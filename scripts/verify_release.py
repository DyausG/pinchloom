"""Reproduce the headless publication checks. Does not open the webcam or UI."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import run  # Use the real launcher's path setup and process-local socket guard.
import numpy as np
from aeropuzzle.calibration import CalibratedHandTracker, fit_profile, pixel_ratio
from aeropuzzle.hand_tracking import HandTracker


def hand(ratio=.2, width=1280, height=720):
    points = [SimpleNamespace(x=100 / width, y=100 / height) for _ in range(21)]
    points[9] = SimpleNamespace(x=100 / width, y=200 / height)
    points[4] = SimpleNamespace(x=200 / width, y=200 / height)
    points[8] = SimpleNamespace(x=(200 + 100 * ratio) / width, y=200 / height)
    return points


class ReleaseChecks(unittest.TestCase):
    def test_preserved_application_bytes(self):
        manifest = json.loads((ROOT / 'docs/evidence/preserved_files.json').read_text())
        for filename, digest in manifest['files'].items():
            with self.subTest(file=filename):
                self.assertEqual(hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(), digest)

    def test_pixel_aspect_and_resolution(self):
        for width, height in [(1280, 720), (640, 480), (960, 540)]:
            with self.subTest(size=(width, height)):
                self.assertAlmostEqual(pixel_ratio(hand(.2, width, height), width, height), .2)

    def test_invalid_measurements(self):
        points = hand()
        points[9] = SimpleNamespace(x=points[0].x, y=points[0].y)
        self.assertIsNone(pixel_ratio(points, 1280, 720))
        points = hand()
        points[3].x = math.nan
        self.assertIsNone(pixel_ratio(points, 1280, 720))
        self.assertIsNone(pixel_ratio(hand(4.1), 1280, 720))

    def test_calibration_rejects_bad_categories(self):
        for opened, pinched in [([1.] * 24, [.1] * 30), ([1.] * 30, [.99] * 30)]:
            with self.assertRaises(ValueError):
                fit_profile(opened, pinched, 'Right')

    def test_personal_hysteresis(self):
        tracker = CalibratedHandTracker.__new__(CalibratedHandTracker)
        tracker.width, tracker.height = 1280, 720
        tracker.profile = {'hand': 'Right', 'close_ratio': .4, 'open_ratio': .7}
        tracker.results = SimpleNamespace(handedness=[[SimpleNamespace(category_name='Right')]])
        tracker._pinch_state = {'Right': False}
        tracker._pinch_start_time = {'Right': 0.}
        tracker.PINCH_CONFIRM_DELAY = .03
        with patch('aeropuzzle.calibration.time.monotonic', return_value=1.):
            self.assertFalse(tracker._update_pinch_for_hand(hand(.2), 0)[0])
        with patch('aeropuzzle.calibration.time.monotonic', return_value=1.04):
            self.assertTrue(tracker._update_pinch_for_hand(hand(.2), 0)[0])
            self.assertTrue(tracker._update_pinch_for_hand(hand(.5), 0)[0])
            self.assertFalse(tracker._update_pinch_for_hand(hand(.8), 0)[0])

    def test_release_to_arm_and_tracking_loss(self):
        tracker = CalibratedHandTracker.__new__(CalibratedHandTracker)
        tracker.profile = {'hand': 'Right', 'open_ratio': .7}
        tracker.phase = 'idle'
        tracker.ratio = .8
        tracker.require_release = True
        tracker.pinch_frames = 0
        tracker.control_index = lambda: 0
        with patch.object(HandTracker, 'get_pinch', return_value=(True, .5, .5)):
            self.assertFalse(tracker.get_pinch()[0])
            self.assertFalse(tracker.require_release)
            self.assertTrue(tracker.get_pinch()[0])
            tracker.control_index = lambda: None
            self.assertFalse(tracker.get_pinch()[0])
            self.assertTrue(tracker.require_release)

    def test_real_dataset_reproduces_fit(self):
        with (ROOT / 'data/calibration_measurements.csv').open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 62)
        opened = [float(row['ratio']) for row in rows if row['pose'] == 'OPEN']
        pinched = [float(row['ratio']) for row in rows if row['pose'] == 'PINCH']
        self.assertEqual((len(opened), len(pinched)), (31, 31))
        self.assertTrue(all(math.isfinite(v) and 0 <= v <= 4 for v in opened + pinched))
        profile = fit_profile(opened, pinched, 'Right')
        metadata = json.loads((ROOT / 'data/metadata.json').read_text())
        for field, expected in metadata['reproduced_fit'].items():
            self.assertAlmostEqual(profile[field], expected, places=12)

    def test_real_model_load_and_blank_image_inference(self):
        # Actual MediaPipe Tasks execution on synthetic blank pixels. No hand
        # detection or fresh-camera accuracy claim is made by this smoke check.
        model = ROOT / 'aeropuzzle_game/aeropuzzle/assets/hand_landmarker.task'
        self.assertEqual(model.stat().st_size, 7819105)
        self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(),
                         'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1')
        tracker = HandTracker()
        try:
            tracker.find_hands(np.zeros((480, 640, 3), dtype=np.uint8))
            self.assertEqual(len(tracker.results.hand_landmarks), 0)
        finally:
            tracker.detector.close()


if __name__ == '__main__':
    for script in ['test_game.py', 'test_pinchloom.py']:
        print(f'Running {script}: scripted headless integration', flush=True)
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts' / script)], cwd=ROOT, check=True)
    unittest.main(verbosity=2)
