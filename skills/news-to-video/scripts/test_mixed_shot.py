"""Protect Blender plate pixels and the opaque pure-SVG render path."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from mixed_shot import (
    PictureState,
    render_states,
    verify_motion_windows,
    verify_overlay_pixels,
)


def png_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class MixedShotTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.job = Path(temporary.name)
        self.folder = self.job / "frames/route"
        self.plate = self.job / "plate.png"
        self.plate_image = Image.new("RGB", (8, 6), (27, 80, 126))
        self.plate_image.putpixel((5, 4), (210, 90, 8))
        self.plate_image.save(self.plate)
        self.page = Mock()

    def render(self, image, states, **kwargs):
        self.page.screenshot.return_value = png_bytes(image)
        render_states(self.job, self.page, states, **kwargs)

    def test_opaque_mixed_screenshot_is_rejected_before_a_frame_is_written(self):
        for alpha in (255, 128):
            with self.subTest(alpha=alpha):
                overlay = Image.new("RGBA", (8, 6), (3, 2, 1, alpha))
                state = PictureState("route", 1, "full-screen", "<svg/>", self.plate)
                with self.assertRaisesRegex(ValueError, "full-screen.*alpha=0"):
                    self.render(overlay, [state])
                self.page.screenshot.assert_called_with(omit_background=True)
                self.assertFalse((self.folder / "000001.png").exists())

    def test_transparent_overlay_keeps_each_plate_and_blends_local_annotations(self):
        overlay = Image.new("RGBA", (8, 6))
        overlay.putpixel((1, 1), (200, 30, 10, 128))
        second_plate = self.job / "second.png"
        second_image = self.plate_image.copy()
        second_image.putpixel((5, 4), (220, 90, 8))
        second_image.save(second_plate)
        states = [
            PictureState("route", 1, "annotation", "<svg/>", self.plate),
            PictureState("route", 2, "annotation", "<svg/>", second_plate),
        ]
        self.render(overlay, states, protected_y=4)
        self.page.screenshot.assert_called_once_with(omit_background=True)

        for frame, plate in enumerate((self.plate_image, second_image), 1):
            with Image.open(self.folder / f"{frame:06d}.png") as composite:
                self.assertEqual(composite.mode, "RGB")
                verify_overlay_pixels(plate, overlay, composite, protected_y=4)
                self.assertEqual(composite.getpixel((5, 4)), plate.getpixel((5, 4)))
                self.assertEqual(composite.getpixel((1, 1)), (114, 55, 68))
        verify_motion_windows(self.folder, [(1, 3)])

    def test_clear_pixel_mismatch_and_protected_rail_are_detected(self):
        overlay = Image.new("RGBA", (8, 6))
        composite = self.plate_image.copy()
        composite.putpixel((5, 4), (210, 90, 9))
        with self.assertRaisesRegex(ValueError, "source plate RGB"):
            verify_overlay_pixels(self.plate_image, overlay, composite)
        overlay.putpixel((6, 4), (200, 30, 10, 1))
        state = PictureState("route", 1, "rail", "<svg/>", self.plate)
        with self.assertRaisesRegex(ValueError, "protected rail at y=4"):
            self.render(overlay, [state], protected_y=4)

    def test_empty_overlay_is_valid_during_a_hold(self):
        overlay = Image.new("RGBA", (8, 6))
        state = PictureState("route", 1, "empty", "<svg/>", self.plate)
        self.render(overlay, [state])
        with Image.open(self.folder / "000001.png") as composite:
            self.assertEqual(composite.tobytes(), self.plate_image.tobytes())

    def test_opaque_pure_2d_stays_rgb_and_reuses_the_raster(self):
        artwork = Image.new("RGBA", (8, 6), (3, 2, 1, 255))
        states = [
            PictureState("route", 1, "2d", "<svg/>"),
            PictureState("route", 2, "2d", "<svg/>"),
        ]
        self.render(artwork, states, protected_y=4)
        self.page.screenshot.assert_called_once_with(omit_background=False)
        with Image.open(self.folder / "000002.png") as frame:
            self.assertEqual(frame.mode, "RGB")
            self.assertEqual(frame.getpixel((2, 5)), (3, 2, 1))

    def test_motion_window_rejects_missing_frames_and_ignores_png_metadata(self):
        self.folder.mkdir(parents=True)
        for frame in (1, 2):
            metadata = PngInfo()
            metadata.add_text("frame", str(frame))
            self.plate_image.save(self.folder / f"{frame:06d}.png", pnginfo=metadata)
        with self.assertRaisesRegex(ValueError, "No decoded picture change"):
            verify_motion_windows(self.folder, [(1, 3)])
        with self.assertRaisesRegex(ValueError, "missing 000003.png"):
            verify_motion_windows(self.folder, [(1, 4)])


if __name__ == "__main__":
    unittest.main()
