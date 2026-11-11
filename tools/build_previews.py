"""Build review excerpts from an existing production; never synthesize a voice.

Public previews deliberately omit the private B voice. Matched voice/mix
excerpts stay in the Git-ignored review directory until publication is cleared.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import imageio_ffmpeg
from PIL import Image, ImageDraw


def run(ffmpeg, *arguments):
    """Keep subprocess arguments separate so paths are never shell commands."""
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *map(str, arguments)],
        check=True,
    )


def build(source, root, music):
    """Derive lightweight previews while preserving the original production."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    public = root / "previews"
    private = root / "local-review"
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    timeline = json.loads((source / "timeline.json").read_text(encoding="utf-8-sig"))
    # Sample each scene, rather than letting a long opening dominate the gallery.
    first_cues = {}
    for cue in timeline:
        first_cues.setdefault(cue["scene"], cue)
    starts = [cue["start"] + 0.5 for cue in first_cues.values()]
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        frames = []
        for index, start in enumerate(starts):
            still = temp / f"frame-{index}.png"
            run(
                ffmpeg,
                "-ss",
                start,
                "-i",
                source / "video.mp4",
                "-frames:v",
                1,
                "-vf",
                "scale=960:-2",
                still,
            )
            with Image.open(still) as frame:
                frames.append(frame.convert("RGB"))
            run(
                ffmpeg,
                "-ss",
                start,
                "-i",
                source / "video.mp4",
                "-t",
                3,
                "-an",
                "-vf",
                "scale=960:-2",
                "-c:v",
                "libx264",
                "-crf",
                23,
                "-pix_fmt",
                "yuv420p",
                temp / f"clip-{index}.mp4",
            )
        concat = temp / "clips.txt"
        concat.write_text(
            "\n".join(f"file 'clip-{index}.mp4'" for index in range(len(starts))),
            encoding="utf-8",
        )
        run(
            ffmpeg,
            "-f",
            "concat",
            "-safe",
            0,
            "-i",
            concat,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            public / "editorial-silent.mp4",
        )
        run(
            ffmpeg,
            "-i",
            public / "editorial-silent.mp4",
            "-filter_complex",
            "fps=6,scale=640:-2,split[a][b];[a]palettegen[p];[b][p]paletteuse",
            "-loop",
            0,
            public / "editorial-preview.gif",
        )
        sheet = Image.new("RGB", (1920, ((len(frames) + 1) // 2) * 576), "#0b1824")
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(frames):
            x, y = (index % 2) * 960, (index // 2) * 576
            sheet.paste(frame, (x, y))
            draw.text(
                (x + 18, y + 548),
                f"SCENE {index + 1:02} / ACTUAL RENDER",
                fill="#d9e5ef",
            )
        sheet.save(public / "contact-sheet.jpg", quality=90)
        frames[0].save(public / "poster.jpg", quality=90)
    run(
        ffmpeg,
        "-i",
        music,
        "-t",
        20,
        "-af",
        "afade=t=in:d=1,afade=t=out:st=18:d=2",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "160k",
        public / "music-preview.mp3",
    )
    # Both excerpts use identical boundaries and no independent loudness matching,
    # so listeners can hear the production mix rather than an altered comparison.
    endpoint = next(
        (cue["end"] for cue in timeline if cue["end"] >= 18), timeline[-1]["end"]
    )
    for source_name, output_name in (
        ("voice.wav", "voice-preview.mp3"),
        ("mix.wav", "mix-preview.mp3"),
    ):
        run(
            ffmpeg,
            "-i",
            source / source_name,
            "-t",
            endpoint,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "160k",
            private / output_name,
        )
    for name in ("video.mp4", "captions.srt", "narration.txt", "音乐署名.txt"):
        shutil.copy2(source / name, private / name)
    original = json.loads((source / "validation.json").read_text(encoding="utf-8-sig"))
    manifest = {
        "sample": "Archived Web3 daily production, 2026-11-11",
        "source_video_sha256": hashlib.sha256(
            (source / "video.mp4").read_bytes()
        ).hexdigest(),
        "original_duration_seconds": original["duration"],
        "original_engine": original["visual_engine"],
        "original_size": [original["width"], original["height"]],
        "silent_montage": {
            "scene_starts": starts,
            "seconds_per_scene": 3,
            "audio": False,
        },
        "music": {
            "title": "Voice Over Under",
            "artist": "Kevin MacLeod",
            "license": "CC BY 4.0",
            "changes": "20s excerpt, fades, MP3 encoding",
        },
        "voice_review": {
            "directory": "local-review (Git ignored)",
            "excerpt_start": 0,
            "excerpt_end": endpoint,
            "publication_rights": "unconfirmed; excluded from Git",
        },
        "limits": [
            "No new reporting or chain verification",
            "No human listening review in this run",
            "Image publication rights and final project license need confirmation",
        ],
    }
    (public / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"scenes": len(starts), "voice_excerpt_seconds": endpoint}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Existing rendered delivery directory",
    )
    parser.add_argument(
        "--music", required=True, type=Path, help="Licensed source track"
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    build(args.source.resolve(), args.root.resolve(), args.music.resolve())
