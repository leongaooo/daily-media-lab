"""Rasterize editable SVG states and layer projected annotations on Blender plates."""

import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops


@dataclass(frozen=True)
class PictureState:
    """A reusable visual state within one shot; frame numbers are one-based."""

    shot: str
    frame: int
    key: str
    svg: str
    plate: Path | None = None


def eased_progress(frame, start, duration):
    """Clamp motion to one cue window and hold both endpoint states."""
    progress = max(0, min(1, (frame - start) / duration))
    return progress * progress * (3 - 2 * progress)


def verify_overlay_pixels(plate, overlay, composite, *, protected_y=None):
    """Check pre-encode RGB against the source plate wherever PNG alpha is zero.

    The optional protected rail starts at protected_y, in image pixels. Empty
    overlay states are valid so an annotation can enter or leave on cue.
    """
    if plate.size != overlay.size or plate.size != composite.size:
        raise ValueError("Plate, overlay and composite dimensions must match")
    alpha = overlay.convert("RGBA").getchannel("A")
    if alpha.getextrema()[0] != 0:
        raise ValueError("Blender overlay has no fully transparent pixels (alpha=0)")
    if protected_y is not None:
        if not 0 <= protected_y < alpha.height:
            raise ValueError("Protected rail must start within the image")
        if alpha.crop((0, protected_y, alpha.width, alpha.height)).getbbox():
            raise ValueError(
                f"Blender overlay reaches the protected rail at y={protected_y}"
            )

    clear_pixels = alpha.point([255] + [0] * 255)
    changed_pixels = ImageChops.difference(
        plate.convert("RGB"), composite.convert("RGB")
    )
    black = Image.new("RGB", plate.size)
    if Image.composite(changed_pixels, black, clear_pixels).getbbox():
        raise ValueError("Composite changes source plate RGB under alpha=0")


def verify_motion_windows(folder, windows):
    """Require decoded RGB to change within each declared one-based [start, end) window."""
    for start, end in windows:
        if start < 1 or end - start < 2:
            raise ValueError(
                f"Motion window [{start}, {end}) needs at least two frames"
            )
        paths = [folder / f"{frame:06d}.png" for frame in range(start, end)]
        for path in paths:
            if not path.is_file():
                raise ValueError(
                    f"Motion window [{start}, {end}) is missing {path.name}"
                )
        with Image.open(paths[0]) as image:
            first = image.convert("RGB")
        for path in paths[1:]:
            with Image.open(path) as image:
                current = image.convert("RGB")
            if current.size != first.size:
                raise ValueError(f"Motion frame dimensions changed at {path.name}")
            if ImageChops.difference(first, current).getbbox():
                break
        else:
            raise ValueError(
                f"No decoded picture change in motion window [{start}, {end})"
            )


def render_states(job, page, states, *, protected_y=None):
    """Rasterize each SVG state once and verify mixed frames before saving RGB masters."""
    sources = job / "source/svg"
    cache = job / "svg-raster"
    sources.mkdir(parents=True, exist_ok=True)
    cache.mkdir(exist_ok=True)
    rasterized = {}
    for state in states:
        key = (state.shot, state.key)
        has_plate = state.plate is not None
        base = f"{state.shot}-{state.key}"
        raster = cache / f"{base}.png"
        if key not in rasterized:
            page.set_content(state.svg, wait_until="load")
            page.add_style_tag(content="body { margin: 0; overflow: hidden; }")
            screenshot = page.screenshot(omit_background=has_plate)
            with Image.open(BytesIO(screenshot)) as image:
                picture = image.convert("RGBA" if has_plate else "RGB")
            if has_plate and picture.getchannel("A").getextrema()[0] != 0:
                raise ValueError(
                    f"{base}: Blender overlay has no fully transparent pixels (alpha=0)"
                )
            (sources / f"{base}.svg").write_text(state.svg, encoding="utf-8")
            # Pure 2D frames may still hard-link the previous cache entry.
            raster.unlink(missing_ok=True)
            picture.save(raster, compress_level=3)
            rasterized[key] = (state.svg, has_plate)
        elif rasterized[key] != (state.svg, has_plate):
            raise ValueError(
                f"SVG state key reused with different artwork or plate mode: {key}"
            )

        folder = job / "frames" / state.shot
        folder.mkdir(parents=True, exist_ok=True)
        frame = folder / f"{state.frame:06d}.png"
        if state.plate is None:
            frame.unlink(missing_ok=True)
            os.link(raster, frame)
        else:
            try:
                with Image.open(state.plate) as plate, Image.open(raster) as overlay:
                    merged = Image.alpha_composite(
                        plate.convert("RGBA"), overlay
                    ).convert("RGB")
                    verify_overlay_pixels(
                        plate, overlay, merged, protected_y=protected_y
                    )
            except ValueError as error:
                raise ValueError(
                    f"{state.shot} frame {state.frame} ({base}): {error}"
                ) from error
            frame.unlink(missing_ok=True)
            merged.save(frame, compress_level=3)
