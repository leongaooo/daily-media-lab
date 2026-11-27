"""Check the two encoded cuts and collect representative frames from the MP4s."""

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

PLAY = """async ({uri, muted}) => {
    const video = document.querySelector("video");
    video.src = uri;
    video.muted = muted;
    const seen = [];
    video.requestVideoFrameCallback(function record(_, meta) {
        seen.push(meta.mediaTime);
        if (!video.ended) video.requestVideoFrameCallback(record);
    });
    const ended = new Promise((resolve, reject) => {
        video.addEventListener("ended", resolve, {once: true});
        video.addEventListener("error", () => reject(video.error.message), {once: true});
        setTimeout(() => reject("Playback exceeded the review window"), 50000);
    });
    const started = performance.now();
    await video.play();
    await ended;
    return {
        ended: video.ended, playback_rate: video.playbackRate,
        wall_seconds: (performance.now() - started) / 1000,
        observed_frames: seen.length, width: video.videoWidth, height: video.videoHeight,
        first_frame_time: seen.at(0), last_frame_time: seen.at(-1),
        dropped_frames: video.getVideoPlaybackQuality().droppedVideoFrames,
        decoded_audio_bytes: video.webkitAudioDecodedByteCount,
    };
}"""


def run(*args):
    return subprocess.check_output([str(arg) for arg in args])


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def frame_images(ffmpeg, path, indexes, folder):
    folder.mkdir(parents=True, exist_ok=True)
    condition = "+".join(f"eq(n,{frame})" for frame in indexes)
    run(
        ffmpeg,
        "-v",
        "error",
        "-y",
        "-i",
        path,
        "-vf",
        f"select='{condition}'",
        "-fps_mode",
        "vfr",
        folder / "%02d.png",
    )
    return [
        Image.open(folder / f"{index:02d}.png").convert("RGB")
        for index in range(1, len(indexes) + 1)
    ]


def milliseconds(stamp):
    hours, minutes, seconds, millis = (int(part) for part in re.split(r"[:,]", stamp))
    return (((hours * 60) + minutes) * 60 + seconds) * 1000 + millis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--skip-player", action="store_true")
    args = parser.parse_args()
    job = args.job
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    review = job / "review"
    review.mkdir(exist_ok=True)
    timing = json.loads((job / "timing.json").read_text(encoding="utf-8"))["boundaries"]
    projection = json.loads((job / "projection.json").read_text(encoding="utf-8"))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    final = output / "IDC-Mixed-Shots.mp4"
    silent = output / "IDC-Mixed-Shots-Silent.mp4"
    captions = output / "IDC-Mixed-Shots.srt"
    import shutil

    shutil.copy2(job / "output/video.mp4", final)
    shutil.copy2(job / "output/captions.srt", captions)
    run(
        ffmpeg,
        "-v",
        "error",
        "-y",
        "-i",
        job / "silent-compose/video.mp4",
        "-map",
        "0:v:0",
        "-c:v",
        "copy",
        "-movflags",
        "+faststart",
        silent,
    )
    assert sha256(job / "output/voice.wav") == sha256(job / "audio/voice.wav")
    if (job / "audio/cues.json").is_file():
        cues = json.loads((job / "audio/cues.json").read_text(encoding="utf-8"))
        srt = captions.read_text(encoding="utf-8-sig").strip().split("\n\n")
        assert len(srt) == len(cues) == 8
        for index, (block, cue) in enumerate(zip(srt, cues)):
            _, window, *text_lines = block.splitlines()
            start, end = (milliseconds(stamp) for stamp in window.split(" --> "))
            assert abs(start - timing[index] / 24 * 1000) < 1
            assert abs(end - timing[index + 1] / 24 * 1000) < 1
            assert "".join(text_lines) == cue["text"]

    indexes = sorted(
        {
            0,
            55,
            timing[1] + 2,
            timing[2] - 1,
            timing[2],
            timing[3] + 14,
            timing[4] + 14,
            timing[5] + 16,
            timing[6] - 1,
            timing[6],
            timing[6] + 12,
            timing[6] + projection["turn_frame"],
            timing[7],
            timing[-1] - 1,
        }
    )
    report = {
        "fps": 24,
        "frames": timing[-1],
        "cue_boundaries": timing,
        "review_frame_indexes": indexes,
        "streams": {},
        "captions_sha256": sha256(captions),
    }
    for name, media in (("voiced", final), ("silent", silent)):
        run(ffmpeg, "-v", "error", "-xerror", "-i", media, "-f", "null", "-")
        data = json.loads(
            run(args.probe, "-v", "error", "-show_streams", "-of", "json", media)
        )
        streams = data["streams"]
        video = streams[0]
        assert (video["width"], video["height"], video["r_frame_rate"]) == (
            1920,
            1080,
            "24/1",
        )
        assert int(video["nb_frames"]) == timing[-1]
        assert [stream["codec_type"] for stream in streams] == (
            ["video", "audio"] if name == "voiced" else ["video"]
        )
        report["streams"][name] = {
            "sha256": sha256(media),
            "bytes": media.stat().st_size,
            "fully_decoded": True,
            "duration": float(video["duration"]),
        }

    front = frame_images(ffmpeg, final, indexes, review / "encoded-voiced")
    back = frame_images(ffmpeg, silent, indexes, review / "encoded-silent")
    main_area, lower_area = [], []
    for voiced, quiet in zip(front, back):
        pixels = np.abs(
            np.asarray(voiced, dtype=np.int16) - np.asarray(quiet, dtype=np.int16)
        )
        main_area.append(round(float(pixels[:904].mean()), 4))
        lower_area.append(round(float(pixels[904:].mean()), 4))
    report["representative_frame_mean_absolute_rgb"] = {
        "main": main_area,
        "caption_rail": lower_area,
    }
    assert max(main_area) < 2.0 and min(lower_area) > 1.0

    sheet = Image.new("RGB", (960, 292 * ((len(front) + 1) // 2)), "#101D29")
    draw = ImageDraw.Draw(sheet)
    for index, (frame, display) in enumerate(zip(indexes, front)):
        x, y = (index % 2) * 480, (index // 2) * 292
        sheet.paste(display.resize((480, 270), Image.Resampling.LANCZOS), (x, y))
        draw.text(
            (x + 9, y + 272), f"{frame / 24:05.2f}s  /  frame {frame}", fill="white"
        )
    sheet.save(output / "IDC-Mixed-Shots-Frames.jpg", quality=90)

    if not args.skip_player:
        player = review / "player.html"
        player.write_text(
            '<meta charset="utf-8"><video width="960" controls playsinline></video>',
            encoding="utf-8",
        )
        report["playback"] = {}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=args.browser,
                args=["--autoplay-policy=no-user-gesture-required"],
            )
            for name, media in (("silent", silent), ("voiced", final)):
                # The local page and media share the file scheme on this review host.
                page = browser.new_page()
                page.goto(player.as_uri())
                result = page.evaluate(
                    PLAY, {"uri": media.as_uri(), "muted": name == "silent"}
                )
                assert result["ended"] and result["playback_rate"] == 1
                assert result["wall_seconds"] > timing[-1] / 24 - 0.5
                assert result["last_frame_time"] >= (timing[-1] - 2) / 24 - 0.001
                if name == "voiced":
                    assert result["decoded_audio_bytes"] > 0
                report["playback"][name] = result
                page.close()
            browser.close()

    (review / "encoded-checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Verified {timing[-1]} frames, {len(indexes)} sampled positions and 8 captions."
    )


if __name__ == "__main__":
    main()
