"""Rasterize editable SVG states and layer projected annotations on Blender plates."""

from dataclasses import dataclass
from pathlib import Path
import os

from PIL import Image


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


def render_states(job, page, states):
    """Save vector source and opaque masters; rasterize identical SVGs only once."""
    sources = job / "source/svg"
    cache = job / "svg-raster"
    sources.mkdir(parents=True, exist_ok=True)
    cache.mkdir(exist_ok=True)
    rasterized = {}
    for state in states:
        key = (state.shot, state.key)
        base = f"{state.shot}-{state.key}"
        raster = cache / f"{base}.png"
        if key not in rasterized:
            rasterized[key] = state.svg
            (sources / f"{base}.svg").write_text(state.svg, encoding="utf-8")
            page.set_content(state.svg, wait_until="load")
            page.add_style_tag(content="body { margin: 0; overflow: hidden; }")
            page.screenshot(path=raster, omit_background=state.plate is not None)
            if state.plate is None:
                with Image.open(raster) as image:
                    rgb = image.convert("RGB")
                rgb.save(raster, compress_level=3)
        elif rasterized[key] != state.svg:
            raise ValueError(f"SVG state key reused with different artwork: {key}")

        folder = job / "frames" / state.shot
        folder.mkdir(parents=True, exist_ok=True)
        frame = folder / f"{state.frame:06d}.png"
        frame.unlink(missing_ok=True)
        if state.plate is None:
            os.link(raster, frame)
        else:
            with Image.open(state.plate) as plate, Image.open(raster) as overlay:
                merged = Image.alpha_composite(
                    plate.convert("RGBA"), overlay.convert("RGBA")
                )
            merged.convert("RGB").save(frame, compress_level=3)
