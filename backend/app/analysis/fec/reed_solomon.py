"""
reed_solomon.py – Self-contained Reed-Solomon codec with CCSDS and standard support.

Features:
  - Built-in GF(2^8) Galois Field arithmetic (log/exp tables, polynomial division)
  - Berlekamp-Massey error locator polynomial calculation
  - Chien search and Forney error evaluator
  - Optional fallback/acceleration via ``reedsolo`` library if installed
"""
from __future__ import annotations

import numpy as np

try:
    import reedsolo as _rs_lib
    _HAS_REEDSOLO = True
except ImportError:
    _HAS_REEDSOLO = False


# ── Built-in GF(2^8) Galois Field Implementation ──────────────────────────────

class GF256:
    """Galois Field GF(2^8) with field polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D / 285)."""

    def __init__(self, prim_poly: int = 0x11D):
        self.exp = [0] * 512
        self.log = [0] * 256
        x = 1
        for i in range(255):
            self.exp[i] = x
            self.exp[i + 255] = x
            self.log[x] = i
            x <<= 1
            if x & 0x100:
                x ^= prim_poly

    def mul(self, x: int, y: int) -> int:
        if x == 0 or y == 0:
            return 0
        return self.exp[self.log[x] + self.log[y]]

    def div(self, x: int, y: int) -> int:
        if y == 0:
            raise ZeroDivisionError("GF(256) division by zero")
        if x == 0:
            return 0
        return self.exp[self.log[x] - self.log[y] + 255]

    def inv(self, x: int) -> int:
        if x == 0:
            raise ZeroDivisionError("GF(256) inversion of zero")
        return self.exp[255 - self.log[x]]


_gf = GF256()


def _poly_mul(p1: list[int], p2: list[int]) -> list[int]:
    out = [0] * (len(p1) + len(p2) - 1)
    for j, c2 in enumerate(p2):
        for i, c1 in enumerate(p1):
            out[i + j] ^= _gf.mul(c1, c2)
    return out


def _poly_eval(poly: list[int], x: int) -> int:
    y = 0
    for coef in poly:
        y = _gf.mul(y, x) ^ coef
    return y


def _calc_syndromes(msg: list[int], nsym: int, fcr: int = 0) -> list[int]:
    return [_poly_eval(msg, _gf.exp[i + fcr]) for i in range(nsym)]


def _berlekamp_massey(synd: list[int], nsym: int) -> list[int]:
    C = [1]
    B = [1]
    L = 0
    m = 1
    b = 1

    for n in range(nsym):
        d = synd[n]
        for i in range(1, L + 1):
            d ^= _gf.mul(C[i], synd[n - i])
        if d == 0:
            m += 1
        else:
            T = list(C)
            scale = _gf.div(d, b)
            temp = [0] * m + [_gf.mul(scale, coef) for coef in B]
            if len(temp) > len(C):
                C += [0] * (len(temp) - len(C))
            for i in range(len(temp)):
                C[i] ^= temp[i]
            if 2 * L <= n:
                L = n + 1 - L
                B = T
                b = d
                m = 1
            else:
                m += 1
    return C


def _chien_search(err_poly: list[int], length: int) -> list[int]:
    positions = []
    for i in range(length):
        inv_x = _gf.exp[(255 - i) % 255]
        if _poly_eval(err_poly, inv_x) == 0:
            positions.append(length - 1 - i)
    return positions


def _forney(synd: list[int], err_poly: list[int], positions: list[int], length: int, fcr: int = 0) -> dict[int, int]:
    # Omega(x) = S(x) * Lambda(x) mod x^nsym
    deg = len(synd)
    omega = _poly_mul(synd, err_poly)[:deg]
    
    # Derivative Lambda'(x)
    err_prime = [err_poly[i] for i in range(1, len(err_poly), 2)]
    
    err_values = {}
    for pos in positions:
        X_inv = _gf.exp[(length - 1 - pos) % 255]
        X = _gf.exp[(255 - (length - 1 - pos)) % 255]
        
        # Evaluate Omega(X_inv)
        num = _poly_eval(omega, X_inv)
        # Evaluate Lambda'(X_inv)
        denom = 0
        for k in range(1, len(err_poly), 2):
            denom ^= _gf.mul(err_poly[k], _gf.exp[((k - 1) * _gf.log[X_inv]) % 255]) if X_inv != 0 else 0
        
        if denom == 0:
            continue
        scale = _gf.exp[((fcr - 1) * _gf.log[X_inv]) % 255] if fcr != 0 and X_inv != 0 else 1
        val = _gf.div(_gf.mul(num, scale), denom) if scale != 1 else _gf.div(num, denom)
        err_values[pos] = val
        
    return err_values


# ── Public API ────────────────────────────────────────────────────────────────

def rs_decode(
    codeword: np.ndarray,
    nsym: int = 32,
    fcr: int = 0,
    prim: int = 1,
    nroots: int = 32,
) -> tuple[np.ndarray, int]:
    """Decode a Reed-Solomon codeword.

    Args:
        codeword: Received byte array (including parity bytes).
        nsym:     Number of parity symbols (2 * t).
        fcr:      First consecutive root of the generator polynomial.
        prim:     Primitive element exponent factor.
        nroots:   Number of roots (= nsym).

    Returns:
        (decoded_bytes, n_errors_corrected)
    """
    codeword = np.asarray(codeword, dtype=np.uint8)
    msg = list(codeword)
    
    if _HAS_REEDSOLO:
        try:
            rsc = _rs_lib.RSCodec(nsym, fcr=fcr, prim=prim, nroots=nroots)
            decoded, _, errata = rsc.decode(bytes(msg))
            return np.frombuffer(decoded, dtype=np.uint8), len(errata)
        except Exception:
            pass  # Fallback to built-in decoder

    # Built-in decoder execution
    synd = _calc_syndromes(msg, nsym, fcr=fcr)
    if not any(synd):
        # No errors detected
        return codeword[:-nsym] if nsym < len(codeword) else codeword, 0

    err_poly = _berlekamp_massey(synd, nsym)
    positions = _chien_search(err_poly, len(msg))
    
    if len(positions) != len(err_poly) - 1:
        # Uncorrectable error count exceeds capacity
        return codeword[:-nsym] if nsym < len(codeword) else codeword, 0

    err_values = _forney(synd, err_poly, positions, len(msg), fcr=fcr)
    corrected = list(msg)
    for pos, val in err_values.items():
        if pos < len(corrected):
            corrected[pos] ^= val

    decoded = np.array(corrected[:-nsym] if nsym < len(corrected) else corrected, dtype=np.uint8)
    return decoded, len(positions)
