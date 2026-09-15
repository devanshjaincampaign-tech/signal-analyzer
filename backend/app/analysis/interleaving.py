import numpy as np


def block_interleave(bits: list[int], rows: int, cols: int) -> list[int]:
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    n = rows * cols
    padded = list(bits[:n]) + [0] * max(0, n - len(bits))
    grid = np.array(padded, dtype=int).reshape(rows, cols)
    return grid.flatten(order="F").tolist()


def block_deinterleave(bits: list[int], rows: int, cols: int) -> list[int]:
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    n = rows * cols
    padded = list(bits[:n]) + [0] * max(0, n - len(bits))
    grid = np.array(padded, dtype=int).reshape(rows, cols, order="F")
    return grid.flatten().tolist()


def _factor_pairs(n: int) -> list[tuple[int, int]]:
    pairs = []
    for rows in range(2, int(n**0.5) + 1):
        if n % rows == 0:
            cols = n // rows
            pairs.append((rows, cols))
            if rows != cols:
                pairs.append((cols, rows))
    return pairs


def _shannon_entropy(bits: list[int]) -> float:
    n_bytes = len(bits) // 8
    if n_bytes == 0:
        return 8.0
    byte_values = [
        int("".join(map(str, bits[i * 8 : (i + 1) * 8])), 2)
        for i in range(n_bytes)
    ]
    counts = np.bincount(byte_values, minlength=256)
    probabilities = counts[counts > 0] / len(byte_values)
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _printable_byte_score(bits: list[int]) -> float:
    n_bytes = len(bits) // 8
    if n_bytes == 0:
        return 0.0
    values = [
        int("".join(map(str, bits[i * 8 : (i + 1) * 8])), 2)
        for i in range(n_bytes)
    ]
    return sum(32 <= value <= 126 for value in values) / n_bytes


def search_deinterleave(bits: list[int], max_candidates: int = 12) -> dict:
    n = len(bits)
    if n < 16:
        return {"success": False, "reason": "Not enough recovered bits to search"}

    candidates = _factor_pairs(n)[:max_candidates]
    if not candidates:
        return {
            "success": False,
            "reason": "Bit count has no usable factor pairs (likely prime length)",
        }

    baseline_entropy = _shannon_entropy(bits)
    results = []
    for rows, cols in candidates:
        deinterleaved = block_deinterleave(bits, rows, cols)
        entropy = _shannon_entropy(deinterleaved)
        results.append(
            {
                "rows": rows,
                "cols": cols,
                "entropy": round(entropy, 4),
                "printable_score": round(_printable_byte_score(deinterleaved), 4),
            }
        )

    results.sort(
        key=lambda result: (-result["printable_score"], result["entropy"])
    )
    best = results[0]
    improvement = baseline_entropy - best["entropy"]
    return {
        "success": True,
        "pattern": "block",
        "best_params": {"rows": best["rows"], "cols": best["cols"]},
        "best_entropy": best["entropy"],
        "baseline_entropy": round(baseline_entropy, 4),
        "entropy_improvement": round(improvement, 4),
        "confidence": round(min(1.0, max(0.0, improvement / 2)), 3),
        "candidates_tried": len(results),
        "top_candidates": results[:5],
    }
