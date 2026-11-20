"""导演事件改变后，声音进退须随同一帧源改变；不触碰冻结干声。"""

import unittest
from pathlib import Path
import tempfile

import numpy as np
import soundfile as sf

from sound_tracks import add_tracks, resolve_event_tracks
from frozen_audio import file_hash


class EventSoundTests(unittest.TestCase):
    def test_fractional_frame_voice_tail_is_preserved(self):
        sample_rate, samples = 24000, 196193
        voice = np.zeros(samples, dtype=np.float32)
        mix = np.zeros((samples, 2), dtype=np.float32)
        events = {"result": {"start_frame": 0, "end_frame": 197}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "air.wav"
            sf.write(path, np.zeros(197000), sample_rate)
            track = {
                "track_id": "tail",
                "path": "air.wav",
                "sha256": file_hash(path),
                "kind": "ambience",
                "gain_db": -50,
                "source_url": "original:test",
                "license": "MIT",
                "attribution": "synthetic boundary fixture",
                "purpose": "test fractional tail without touching frozen voice",
                "timing": {"start_event": "result", "end_event": "result"},
            }
            with self.assertRaisesRegex(ValueError, "range"):
                add_tracks(
                    mix,
                    voice,
                    sample_rate,
                    resolve_event_tracks([track], events, 24),
                    folder,
                )
            track["timing"]["end_offset_frames"] = -1
            output, receipt = add_tracks(
                mix,
                voice,
                sample_rate,
                resolve_event_tracks([track], events, 24),
                folder,
            )
            self.assertEqual(len(output), samples)
            self.assertEqual(receipt[0]["decoded_samples_used"], 196000)
            self.assertTrue(np.array_equal(voice, np.zeros(samples, dtype=np.float32)))

    def test_shifted_event_moves_track_without_mutating_input(self):
        tracks = [
            {
                "track_id": "panel",
                "timing": {"start_event": "panel", "end_event": "panel"},
            }
        ]
        first = resolve_event_tracks(
            tracks, {"panel": {"start_frame": 24, "end_frame": 48}}, 24
        )
        shifted = resolve_event_tracks(
            tracks, {"panel": {"start_frame": 48, "end_frame": 72}}, 24
        )
        self.assertEqual((first[0]["start"], shifted[0]["start"]), (1, 2))
        self.assertEqual(first[0]["duration"], shifted[0]["duration"])
        self.assertNotIn("start", tracks[0])

    def test_absolute_and_event_timing_cannot_compete(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            resolve_event_tracks([{"start": 0, "timing": {}}], {}, 24)

    def test_unknown_event_and_reverse_interval_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "existing"):
            resolve_event_tracks([{"timing": {"start_event": "absent"}}], {}, 24)
        with self.assertRaisesRegex(ValueError, "positive"):
            resolve_event_tracks(
                [{"timing": {"start_event": "x", "end_event": "x"}}],
                {"x": {"start_frame": 48, "end_frame": 24}},
                24,
            )


if __name__ == "__main__":
    unittest.main()
