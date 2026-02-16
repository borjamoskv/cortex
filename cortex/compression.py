"""CORTEX v4.1 — Embedding Compression.

int8 quantization for embedding storage. Reduces storage from 1.5KB to 388 bytes
per vector (3.9x compression). Search quality impact is negligible for
normalized embeddings from all-MiniLM-L6-v2.

Storage format: [4 bytes float32 scale] + [384 bytes int8 values] = 388 bytes
vs original: [384 × 4 bytes float32] = 1,536 bytes (JSON is even larger)
"""
from __future__ import annotations

import struct
import logging
from typing import List

logger = logging.getLogger("cortex.embeddings.compression")

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    _NP_AVAILABLE = False
    logger.debug("numpy not available — embedding compression disabled")


def quantize_int8(embedding: List[float]) -> bytes:
    """Quantize float32 embedding to int8 (3.9x storage reduction).

    Stores a single float32 scale factor followed by 384 int8 values.
    Total: 4 + 384 = 388 bytes vs 1,536 bytes (float32) or ~2,500 bytes (JSON).

    Args:
        embedding: List of floats (typically 384-dim from MiniLM).

    Returns:
        Packed bytes: [scale:f32][values:int8×N]
    """
    if not _NP_AVAILABLE:
        raise RuntimeError("numpy required for embedding compression")

    arr = np.array(embedding, dtype=np.float32)
    abs_max = max(abs(arr.max()), abs(arr.min()))
    scale = abs_max if abs_max > 0 else 1.0

    quantized = np.clip(
        np.round(arr / scale * 127), -128, 127
    ).astype(np.int8)

    return struct.pack("f", scale) + quantized.tobytes()


def dequantize_int8(data: bytes) -> List[float]:
    """Dequantize int8 back to float32 for search.

    Args:
        data: Bytes from quantize_int8().

    Returns:
        List of float32 values (approximate reconstruction).
    """
    if not _NP_AVAILABLE:
        raise RuntimeError("numpy required for embedding decompression")

    scale = struct.unpack("f", data[:4])[0]
    quantized = np.frombuffer(data[4:], dtype=np.int8)
    return (quantized.astype(np.float32) * scale / 127.0).tolist()


def compression_ratio(dim: int = 384) -> dict:
    """Report compression statistics for a given embedding dimension.

    Returns:
        Dict with original, compressed sizes and ratio.
    """
    original_float32 = dim * 4  # bytes
    original_json = dim * 7  # approx bytes in JSON "[0.123, ...]"
    compressed = 4 + dim  # scale + int8 values
    return {
        "dim": dim,
        "float32_bytes": original_float32,
        "json_approx_bytes": original_json,
        "int8_bytes": compressed,
        "ratio_vs_float32": round(original_float32 / compressed, 1),
        "ratio_vs_json": round(original_json / compressed, 1),
    }
