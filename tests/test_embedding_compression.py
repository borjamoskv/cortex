"""Tests for CORTEX v4.1 — Embedding Compression (int8 Quantization).

Tests quantize/dequantize roundtrip, compression ratio, and edge cases.
"""

import pytest
from cortex.compression import quantize_int8, dequantize_int8, compression_ratio

try:
    import numpy as np

    _NP_AVAILABLE = True
except ImportError:
    _NP_AVAILABLE = False


@pytest.mark.skipif(not _NP_AVAILABLE, reason="numpy required")
class TestInt8Quantization:
    """Tests for int8 quantize/dequantize roundtrip."""

    def test_roundtrip_preserves_shape(self):
        """Dequantized output should have same length as input."""
        embedding = [0.1] * 384
        packed = quantize_int8(embedding)
        restored = dequantize_int8(packed)
        assert len(restored) == 384

    def test_roundtrip_low_error(self):
        """Roundtrip quantization error should be negligible for normalized vectors."""
        np.random.seed(42)
        # Generate a unit-normalized embedding like MiniLM produces
        raw = np.random.randn(384).astype(np.float32)
        normalized = (raw / np.linalg.norm(raw)).tolist()

        packed = quantize_int8(normalized)
        restored = dequantize_int8(packed)

        # Max absolute error should be < 0.02 for normalized vectors
        errors = [abs(a - b) for a, b in zip(normalized, restored)]
        max_error = max(errors)
        assert max_error < 0.02, f"max error {max_error:.6f} exceeds threshold"

    def test_cosine_similarity_preserved(self):
        """Cosine similarity between original and reconstructed should be > 0.99."""
        np.random.seed(42)
        raw = np.random.randn(384).astype(np.float32)
        normalized = raw / np.linalg.norm(raw)

        packed = quantize_int8(normalized.tolist())
        restored = np.array(dequantize_int8(packed))

        cos_sim = np.dot(normalized, restored) / (
            np.linalg.norm(normalized) * np.linalg.norm(restored)
        )
        assert cos_sim > 0.99, f"cosine similarity {cos_sim:.6f} too low"

    def test_packed_size(self):
        """int8 packed: 4 bytes scale + 384 bytes = 388 bytes."""
        embedding = [0.1] * 384
        packed = quantize_int8(embedding)
        assert len(packed) == 388  # 4 (float32 scale) + 384 (int8 values)

    def test_zero_embedding(self):
        """All-zero embedding should not crash and roundtrip safely."""
        zeros = [0.0] * 384
        packed = quantize_int8(zeros)
        restored = dequantize_int8(packed)
        assert all(v == 0.0 for v in restored)

    def test_extreme_values(self):
        """Extreme float values should be handled without overflow."""
        extreme = [1e6] * 192 + [-1e6] * 192
        packed = quantize_int8(extreme)
        restored = dequantize_int8(packed)
        assert len(restored) == 384

    def test_single_value_embedding(self):
        """1-dim embedding should work."""
        single = [0.5]
        packed = quantize_int8(single)
        restored = dequantize_int8(packed)
        assert len(restored) == 1
        assert abs(restored[0] - 0.5) < 0.01


class TestCompressionRatio:
    """Tests for compression_ratio() reporting."""

    def test_default_384d(self):
        """Default 384-dim should report ~3.9x compression."""
        stats = compression_ratio()
        assert stats["dim"] == 384
        assert stats["float32_bytes"] == 1536
        assert stats["int8_bytes"] == 388
        assert stats["ratio_vs_float32"] >= 3.5

    def test_custom_dim(self):
        """Custom dimension should compute correctly."""
        stats = compression_ratio(dim=768)
        assert stats["dim"] == 768
        assert stats["int8_bytes"] == 772  # 4 + 768
