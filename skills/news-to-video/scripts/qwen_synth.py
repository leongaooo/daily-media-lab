"""由已配置的 Qwen 解释器运行；内置音色与私人参考严格分派，无换声回退。"""

import argparse
import gc
import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf

from voice_backend import load_profile, read_json
from public_voice import PUBLIC_VOICE_ID


def prepare_audio(audio, sample_rate):
    """统一边界裁静音和峰值处理，不改音高或播放速度。"""
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim != 1 or len(audio) < sample_rate // 5 or not np.isfinite(audio).all():
        raise ValueError("Qwen produced empty, short or non-finite speech")
    active = np.flatnonzero(np.abs(audio) > 0.003)
    if not len(active):
        raise ValueError("Qwen produced silence")
    left = max(0, active[0] - int(0.12 * sample_rate))
    right = min(len(audio), active[-1] + int(0.20 * sample_rate))
    audio = audio[left:right].copy()
    audio *= min(0.89 / max(float(np.max(np.abs(audio))), 1e-6), 3.0)
    return audio


def run(request_path, check_only=False):
    # 离线标志须在导入 transformers 前设置；缺模型时明确失败。
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from qwen_tts import Qwen3TTSModel

    request = read_json(request_path)
    profile, identity = load_profile(request["runtime"], verify_weights=False)
    if not torch.cuda.is_available():
        raise RuntimeError(
            "The configured Qwen backend requires CUDA; no fallback voice is allowed"
        )
    if check_only:
        print(
            json.dumps(
                {
                    "ok": True,
                    "voice_id": identity["voice_id"],
                    "cuda": torch.cuda.get_device_name(0),
                }
            )
        )
        return
    torch.set_num_threads(6)
    print("Loading configured voice backend", flush=True)
    model = Qwen3TTSModel.from_pretrained(
        profile["model_dir"],
        # Windows 上直接向 CUDA 映射 safetensors 切片会在 storage 索引中
        # 原生崩溃；先在 CPU 完成同一权重加载，再整体转移到 GPU 推理。
        device_map="cpu",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        local_files_only=True,
    )
    device = torch.device("cuda:0")
    model.model.to(device)
    model.device = device
    # 语音 tokenizer 是包装对象，不随主 nn.Module 自动搬移。
    tokenizer = model.model.speech_tokenizer
    tokenizer.model.to(device)
    tokenizer.device = device
    public = identity["voice_id"] == PUBLIC_VOICE_ID
    prompt = None
    if not public:
        reference, reference_rate = sf.read(profile["reference_audio"], dtype="float32")
        prompt = model.create_voice_clone_prompt(
            ref_audio=(reference, reference_rate),
            ref_text=profile["reference_text"],
            x_vector_only_mode=False,
        )
    settings = dict(profile["settings"])
    seed = settings.pop("seed")
    for job in request["jobs"]:
        torch.manual_seed(seed)
        with torch.inference_mode():
            if public:
                waves, sample_rate = model.generate_custom_voice(
                    text=job["text"],
                    language=profile["language"],
                    speaker=profile["speaker"],
                    non_streaming_mode=True,
                    **settings,
                )
            else:
                waves, sample_rate = model.generate_voice_clone(
                    text=job["text"],
                    language="Chinese",
                    voice_clone_prompt=prompt,
                    non_streaming_mode=True,
                    **settings,
                )
        audio = prepare_audio(waves[0], sample_rate)
        path = Path(job["output"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".partial.wav")
        sf.write(temporary, audio, sample_rate, subtype="PCM_16")
        temporary.replace(path)
        print(f"Configured voice synthesized: {job['text']}", flush=True)
        del waves, audio
        gc.collect()
        torch.cuda.empty_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.request, args.check)
