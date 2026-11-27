"""Read Qwen model weights through the runtime's platform-specific loader."""

from functools import partial
import os


def load_qwen_weights(load_model, model_dir, **options):
    """Use explicit CPU weight reads on Windows for both model and tokenizer."""
    if os.name != "nt":
        return load_model(model_dir, **options)

    from transformers import modeling_utils

    # Transformers indexes safetensors slices during from_pretrained. Windows
    # can fault on the mmap path even when the destination is CPU.
    original_reader = modeling_utils.safe_open
    modeling_utils.safe_open = partial(original_reader, backend="pread")
    try:
        return load_model(model_dir, **options)
    finally:
        modeling_utils.safe_open = original_reader
