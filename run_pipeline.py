"""
run_pipeline.py – High-Performance Signal Analysis Pipeline with Ultra-High-Resolution Visualizations.

Features:
  - Robust Sampling Rate Detection (SigMF metadata, Filename regex, and CLI --sample-rate override)
  - Automatic binary IQ format autodetection (float32, int16, int8, uint8)
  - 3 Separate Ultra-High-Resolution (300 DPI) Engineering Plots:
      1. <name>_psd_spectrum.png          : Power Spectral Density with fc & 3dB bandwidth markers
      2. <name>_spectrogram_waterfall.png : Calibrated Time-Frequency Spectrogram with Colorbar
      3. <name>_constellation.png         : In-Phase vs Quadrature Constellation Diagram
  - Complete output artifacts:
      - <name>_summary.txt                : Human-readable parameter extraction summary
      - <name>_report.json                : Machine-readable JSON report
      - <name>_payload.txt / .bin         : Decoded bitstream and payload (Header isolated)
      - index.html                        : Responsive interactive dashboard
"""
from __future__ import annotations

import os
import sys
import glob
import json
import argparse
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(CURRENT_DIR, "backend") if os.path.exists(os.path.join(CURRENT_DIR, "backend")) else CURRENT_DIR
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.routers.analysis import _execute_full_pipeline
from app.ingestion.iq_reader import read_iq_samples, parse_sample_rate
from app.schemas import DirectAnalysisRequest
import soundfile as sf

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False


def _load_signal_file(path: str, sample_rate_override: float | None = None) -> tuple[np.ndarray, float, bool]:
    """Load .wav or .iq file with sample rate autodetection and override support."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "wav":
        data, sr = sf.read(path)
        if data.ndim > 1:
            data = data[:, 0]
        final_sr = float(sample_rate_override if sample_rate_override and sample_rate_override > 0 else sr)
        return data.astype(np.float32), final_sr, False

    elif ext in ("iq", "sigmf-meta"):
        iq_path = path if ext == "iq" else path.rsplit(".", 1)[0] + ".iq"
        iq, sr, _ = read_iq_samples(iq_path, sample_rate_override=sample_rate_override)
        return iq, sr, True

    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def _format_freq(hz: float) -> tuple[float, str]:
    """Convert Hz to kHz or MHz depending on magnitude."""
    if abs(hz) >= 1e6:
        return hz / 1e6, "MHz"
    elif abs(hz) >= 1e3:
        return hz / 1e3, "kHz"
    return hz, "Hz"


# ── Standalone Ultra-High-Resolution Plot Generators ──────────────────────────

def save_psd_plot(results: dict, output_path: str, filename: str) -> None:
    """Generate separate Ultra-High-Resolution (300 DPI) PSD plot with peak and bandwidth markers."""
    if not _HAS_MPL:
        return

    freqs = np.array(results.get("freqs", []))
    psd_db = np.array(results.get("psd", []))
    feat = results.get("features", {})
    sr = feat.get("sample_rate_used", 1_000_000.0)
    fc = feat.get("center_frequency_hz", 0.0)
    bw = feat.get("bandwidth_hz", 0.0)

    _, freq_unit = _format_freq(sr / 2.0)
    scale_factor = 1e6 if freq_unit == "MHz" else (1e3 if freq_unit == "kHz" else 1.0)

    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    fig.patch.set_facecolor("#ffffff")

    if len(freqs) > 0 and len(psd_db) > 0:
        f_scaled = freqs / scale_factor
        ax.plot(f_scaled, psd_db, color="#1f77b4", lw=2.2, label="Power Spectral Density (Welch PSD)")

        # Center frequency marker line
        fc_scaled = fc / scale_factor
        ax.axvline(fc_scaled, color="#d62728", ls="--", lw=2.0, label=f"Center Freq (fc): {fc/scale_factor:.3f} {freq_unit}")

        # Occupied 3dB bandwidth shaded area
        if bw > 0:
            bw_left = (fc - bw / 2.0) / scale_factor
            bw_right = (fc + bw / 2.0) / scale_factor
            ax.axvspan(bw_left, bw_right, color="#2ca02c", alpha=0.18, label=f"Occupied 3dB BW: {bw/scale_factor:.3f} {freq_unit}")

        ax.set_title(f"Power Spectral Density (PSD) – {filename}\n[Fs = {sr:,.1f} Hz]", fontsize=16, fontweight="bold", pad=14)
        ax.set_xlabel(f"Frequency ({freq_unit})", fontsize=14, fontweight="bold", labelpad=10)
        ax.set_ylabel("Spectral Power (dBFS)", fontsize=14, fontweight="bold", labelpad=10)
        ax.tick_params(axis="both", which="major", labelsize=12)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right", fontsize=12, framealpha=0.95, edgecolor="#cccccc")
    else:
        ax.text(0.5, 0.5, "No PSD data available", ha="center", va="center", fontsize=16)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)


def save_spectrogram_plot(results: dict, output_path: str, filename: str) -> None:
    """Generate separate Ultra-High-Resolution (300 DPI) Spectrogram / Waterfall plot."""
    if not _HAS_MPL:
        return

    spectrogram = results.get("spectrogram", {})
    feat = results.get("features", {})
    sr = feat.get("sample_rate_used", 1_000_000.0)

    _, freq_unit = _format_freq(sr / 2.0)
    scale_factor = 1e6 if freq_unit == "MHz" else (1e3 if freq_unit == "kHz" else 1.0)

    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    fig.patch.set_facecolor("#ffffff")

    if "power_db_matrix" in spectrogram and len(spectrogram["power_db_matrix"]) > 0:
        mat = np.array(spectrogram["power_db_matrix"]).T
        time_bins = np.array(spectrogram.get("time_bins", [0, 1])) * 1e3  # convert to ms
        freq_bins = np.array(spectrogram.get("freq_bins", [-sr/2, sr/2])) / scale_factor

        extent = [freq_bins[0], freq_bins[-1], time_bins[0], time_bins[-1]]
        vmin = float(np.percentile(mat, 5))
        vmax = float(np.max(mat))

        im = ax.imshow(
            mat, aspect="auto", origin="lower", extent=extent,
            cmap="inferno", interpolation="bilinear", vmin=vmin, vmax=vmax
        )
        ax.set_title(f"Spectrogram / Waterfall (Time vs Frequency) – {filename}\n[Fs = {sr:,.1f} Hz]", fontsize=16, fontweight="bold", pad=14)
        ax.set_xlabel(f"Frequency ({freq_unit})", fontsize=14, fontweight="bold", labelpad=10)
        ax.set_ylabel("Time (ms)", fontsize=14, fontweight="bold", labelpad=10)
        ax.tick_params(axis="both", which="major", labelsize=12)

        cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.046)
        cbar.set_label("Spectral Density (dBFS)", fontsize=13, fontweight="bold", labelpad=10)
        cbar.ax.tick_params(labelsize=11)
    else:
        ax.text(0.5, 0.5, "No Spectrogram data available", ha="center", va="center", fontsize=16)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)


def save_constellation_plot(results: dict, output_path: str, filename: str) -> None:
    """Generate separate Ultra-High-Resolution (300 DPI) I/Q Constellation Diagram."""
    if not _HAS_MPL:
        return

    iq_samples = results.get("iq_samples", {})
    clf = results.get("classification", {})
    mod = clf.get("modulation", "Unknown")
    conf = clf.get("confidence", 0.0)

    fig, ax = plt.subplots(figsize=(9, 9), dpi=300)
    fig.patch.set_facecolor("#ffffff")

    if "i" in iq_samples and "q" in iq_samples:
        i_pts = np.array(iq_samples["i"])
        q_pts = np.array(iq_samples["q"])

        # Reference unit circle and crosshairs
        circle = plt.Circle((0, 0), 1.0, color="#888888", fill=False, ls="--", lw=1.5, alpha=0.7, label="Unit Circle (|r|=1)")
        ax.add_patch(circle)
        ax.axhline(0, color="#888888", lw=1.2, ls=":")
        ax.axvline(0, color="#888888", lw=1.2, ls=":")

        # Scatter plot
        ax.scatter(i_pts, q_pts, s=24, color="#ff7f0e", alpha=0.65, edgecolors="#d95f02", lw=0.4, label="IQ Symbols")

        ax.set_title(f"IQ Constellation Diagram – {filename}\n[Detected Modulation: {mod} ({conf:.1%})]", fontsize=15, fontweight="bold", pad=14)
        ax.set_xlabel("In-Phase (I)", fontsize=14, fontweight="bold", labelpad=10)
        ax.set_ylabel("Quadrature (Q)", fontsize=14, fontweight="bold", labelpad=10)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-1.8, 1.8)
        ax.set_ylim(-1.8, 1.8)
        ax.tick_params(axis="both", which="major", labelsize=12)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper right", fontsize=11, framealpha=0.95, edgecolor="#cccccc")
    else:
        ax.text(0.5, 0.5, "No Constellation data available", ha="center", va="center", fontsize=16)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)


# ── Interactive HTML Dashboard ────────────────────────────────────────────────

def _generate_html_dashboard(all_summaries: list[dict], output_dir: str) -> str:
    """Generate clean HTML dashboard displaying individual high-resolution plots."""
    cards_html = []
    for s in all_summaries:
        fname = s["filename"]
        stem = os.path.splitext(fname)[0]
        feat = s.get("features", {})
        sym = s.get("symbol_rate", {})
        clf = s.get("classification", {})
        fec = s.get("fec", {})
        corr = s.get("correlation", {})

        cards_html.append(f"""
        <div class="card">
            <h2>🛰️ {fname}</h2>
            <div class="grid">
                <div><strong>Sampling Rate:</strong> {feat.get('sample_rate_used', 0):,.1f} Hz</div>
                <div><strong>Carrier Freq:</strong> {feat.get('center_frequency_hz', 0):,.1f} Hz</div>
                <div><strong>Bandwidth (3dB):</strong> {feat.get('bandwidth_hz', 0):,.1f} Hz</div>
                <div><strong>Modulation:</strong> <span class="badge badge-mod">{clf.get('modulation', 'N/A')} ({clf.get('confidence', 0):.0%})</span></div>
                <div><strong>Symbol Rate:</strong> {sym.get('symbol_rate_hz', 0):,.1f} sym/s</div>
                <div><strong>FEC Codec:</strong> {fec.get('method', 'None')}</div>
                <div><strong>Sync Matches:</strong> {corr.get('total_hits', 0)} header(s)</div>
            </div>

            <div class="plots-grid">
                <div class="plot-item">
                    <h4>1. Power Spectral Density (PSD)</h4>
                    <a href="{stem}_psd_spectrum.png" target="_blank">
                        <img src="{stem}_psd_spectrum.png" alt="PSD Plot" />
                    </a>
                </div>
                <div class="plot-item">
                    <h4>2. Spectrogram / Waterfall</h4>
                    <a href="{stem}_spectrogram_waterfall.png" target="_blank">
                        <img src="{stem}_spectrogram_waterfall.png" alt="Waterfall Plot" />
                    </a>
                </div>
                <div class="plot-item">
                    <h4>3. IQ Constellation</h4>
                    <a href="{stem}_constellation.png" target="_blank">
                        <img src="{stem}_constellation.png" alt="Constellation Plot" />
                    </a>
                </div>
            </div>

            <div class="links">
                <a href="{stem}_summary.txt" target="_blank">📄 Text Summary</a> &bull;
                <a href="{stem}_report.json" target="_blank">🔍 JSON Report</a> &bull;
                <a href="{stem}_payload.txt" target="_blank">💾 Decoded Payload</a>
            </div>
        </div>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Signal Analyzer - Extraction Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 25px; }}
        h1 {{ color: #1a202c; text-align: center; margin-bottom: 25px; }}
        .card {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); padding: 24px; margin-bottom: 35px; }}
        .card h2 {{ margin-top: 0; color: #2b6cb0; font-size: 1.4rem; border-bottom: 2px solid #edf2f7; padding-bottom: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; font-size: 0.95rem; margin-bottom: 20px; }}
        .badge {{ padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }}
        .badge-mod {{ background: #ebf8ff; color: #2b6cb0; }}
        .plots-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-top: 15px; }}
        .plot-item {{ background: #fafafa; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }}
        .plot-item h4 {{ margin: 0 0 10px 0; font-size: 1rem; color: #4a5568; }}
        .plot-item img {{ width: 100%; border-radius: 6px; display: block; }}
        .links {{ margin-top: 18px; font-size: 0.95rem; }}
        .links a {{ color: #3182ce; text-decoration: none; font-weight: 500; }}
        .links a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🛰️ Automated Signal Parameter Extraction & Analysis Dashboard</h1>
    {"".join(cards_html)}
</body>
</html>"""
    dashboard_path = os.path.join(output_dir, "index.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return dashboard_path


# ── File Analysis Pipeline ────────────────────────────────────────────────────

def analyze_single_file(file_path: str, output_dir: str, sample_rate_override: float | str | None = None) -> dict:
    """Run full pipeline on one file and generate all separate outputs."""
    base_name = os.path.basename(file_path)
    file_stem = os.path.splitext(base_name)[0]
    os.makedirs(output_dir, exist_ok=True)

    sr_override_val = parse_sample_rate(sample_rate_override)
    print(f"\n[{base_name}] Loading and executing analysis...")
    sig, sample_rate, is_complex = _load_signal_file(file_path, sample_rate_override=sr_override_val)

    # 1. Run Complete Analysis Pipeline
    req = DirectAnalysisRequest(sample_rate_override=sr_override_val)
    results = _execute_full_pipeline(sig, sample_rate, req)
    results["filename"] = base_name

    feat = results.get("features", {})
    sym = results.get("symbol_rate", {})
    clf = results.get("classification", {})
    dem = results.get("demod", {})
    intlv = results.get("interleaving", {})
    fec = results.get("fec", {})
    corr = results.get("correlation", {})

    # 2. Save JSON Report
    json_path = os.path.join(output_dir, f"{file_stem}_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # 3. Separate Header vs Payload & Save Decoded Files
    recovered_bits = (
        fec.get("decoded_bits")
        or (intlv.get("bits") if intlv.get("success") else None)
        or dem.get("bits")
    )

    header_info = "None detected"
    payload_offset = 0
    if corr.get("hits"):
        for sw_name, hit_list in corr["hits"].items():
            if hit_list:
                header_info = f"{sw_name.upper()} at bit offset {hit_list[0]['offset']}"
                payload_offset = hit_list[0]["offset"]
                break

    if recovered_bits and len(recovered_bits) >= 8:
        bit_arr = np.array(recovered_bits, dtype=np.uint8)
        n_bytes = len(bit_arr) // 8
        byte_data = np.packbits(bit_arr[:n_bytes * 8]).tobytes()

        # Binary output
        bin_path = os.path.join(output_dir, f"{file_stem}_payload.bin")
        with open(bin_path, "wb") as f:
            f.write(byte_data)

        # Formatted Payload with Header/Payload Isolation
        txt_path = os.path.join(output_dir, f"{file_stem}_payload.txt")
        hex_dump = " ".join(f"{b:02X}" for b in byte_data[:64])
        printable_ascii = "".join(chr(b) if 32 <= b <= 126 or b in (10, 13, 9) else "." for b in byte_data)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("======================================================================\n")
            f.write(f"DECODED BITSTREAM & PAYLOAD EXTRACTION: {base_name}\n")
            f.write("======================================================================\n\n")
            f.write(f"[1] FRAME SYNCHRONIZATION / HEADER IDENTIFICATION:\n")
            f.write(f"    - Detected Header Pattern: {header_info}\n")
            f.write(f"    - Total Sync Words Found : {corr.get('total_hits', 0)}\n")
            f.write(f"    - Payload Start Offset   : Bit {payload_offset}\n\n")
            f.write(f"[2] BITSTREAM RECOVERY:\n")
            f.write(f"    - Total Bits Recovered   : {len(recovered_bits)}\n")
            f.write(f"    - Bit Stream (first 160) : {''.join(map(str, recovered_bits[:160]))}...\n\n")
            f.write(f"[3] HEXADECIMAL DUMP (First 64 Bytes):\n")
            f.write(f"    {hex_dump}...\n\n")
            f.write(f"[4] RECOVERED ASCII PAYLOAD:\n")
            f.write(f"    {printable_ascii}\n")
            f.write("======================================================================\n")

    # 4. Formatted Text Summary Report
    summary_txt_path = os.path.join(output_dir, f"{file_stem}_summary.txt")
    with open(summary_txt_path, "w", encoding="utf-8") as f:
        f.write("======================================================================\n")
        f.write(f"SIGNAL ANALYSIS & PARAMETER EXTRACTION REPORT: {base_name}\n")
        f.write("======================================================================\n\n")
        was_assumed = feat.get('sample_rate_was_assumed', False)
        sr_tag = " (Assumed default - pass --sample-rate to override)" if was_assumed else ""
        f.write("1. INGESTION & SPECTRAL CHARACTERISTICS:\n")
        f.write(f"   - Sampling Rate (Fs)       : {feat.get('sample_rate_used', 0):,.2f} Hz{sr_tag}\n")
        f.write(f"   - Center Frequency (fc)    : {feat.get('center_frequency_hz', 0):>+15,.2f} Hz (Baseband Offset from SDR LO)\n")
        f.write(f"   - Occupied Bandwidth (3dB) : {feat.get('bandwidth_hz', 0):>15,.2f} Hz (Contiguous channel lobe)\n")
        if feat.get('bandwidth_10db_hz'):
            f.write(f"   - Occupied Bandwidth (10dB): {feat.get('bandwidth_10db_hz', 0):>15,.2f} Hz\n")
        f.write(f"   - Peak Spectral Power      : {feat.get('peak_power_db', 0):.2f} dBFS\n")
        f.write(f"   - Average Noise Floor      : {feat.get('noise_floor_db', 0):.2f} dBFS\n\n")
        f.write("2. MODULATION & SYMBOL TIMING:\n")
        clf_top = ", ".join(f"{c['label']}({c['score']:.0%})" for c in clf.get("candidates", [])[:3])
        f.write(f"   - Detected Modulation      : {clf.get('modulation', 'Unknown')} "
                f"(Confidence: {clf.get('confidence', 0):.1%}, "
                f"Method: {clf.get('method', 'rule_based')})\n")
        f.write(f"   - Top Candidates           : {clf_top or 'N/A'}\n")
        f.write(f"   - Estimated Symbol Rate    : {sym.get('symbol_rate_hz', 0):,.2f} sym/s\n")
        f.write(f"   - Samples per Symbol (SPS) : {sym.get('samples_per_symbol', 'N/A')}\n\n")
        f.write("3. DEMODULATION & DE-INTERLEAVING:\n")
        f.write(f"   - Demodulator Output Type  : {dem.get('type', 'N/A')}\n")
        f.write(f"   - Recovered Raw Bits       : {dem.get('num_bits', 0)}\n")
        f.write(f"   - De-interleaver Pattern   : {intlv.get('pattern', 'None')}\n")
        f.write(f"   - De-interleaver Parameters: {intlv.get('best_params', {})}\n\n")
        f.write("4. FORWARD ERROR CORRECTION (FEC):\n")
        f.write(f"   - Codec Scheme Applied     : {fec.get('method', 'None')}\n")
        f.write(f"   - Error Corrected Bitcount : {fec.get('decoded_count', 0)}\n\n")
        f.write("5. BITSTREAM CORRELATION & HEADER IDENTIFICATION:\n")
        f.write(f"   - Header Synchronization   : {header_info}\n")
        f.write(f"   - Total Sync Matches       : {corr.get('total_hits', 0)}\n")
        f.write("======================================================================\n")

    # 5. Generate 3 Separate Ultra-High-Resolution (300 DPI) Plots
    psd_img_path = os.path.join(output_dir, f"{file_stem}_psd_spectrum.png")
    spec_img_path = os.path.join(output_dir, f"{file_stem}_spectrogram_waterfall.png")
    const_img_path = os.path.join(output_dir, f"{file_stem}_constellation.png")

    save_psd_plot(results, psd_img_path, base_name)
    save_spectrogram_plot(results, spec_img_path, base_name)
    save_constellation_plot(results, const_img_path, base_name)

    # 6. Terminal Summary Card
    print("+" + "-" * 70 + "+")
    print(f"| RESULTS FOR: {base_name:<55} |")
    print("+" + "-" * 70 + "+")
    was_assumed = feat.get('sample_rate_was_assumed', False)
    sr_str = f"{feat.get('sample_rate_used', 0):>15,.1f} Hz"
    if was_assumed:
        sr_str += " [DEFAULT ASSUMED]"
    print(f"| Sampling Rate (Fs): {sr_str}")
    print(f"| Carrier Freq (fc) : {feat.get('center_frequency_hz', 0):>+15,.1f} Hz (Baseband Offset)")
    print(f"| Occupied Bandwidth: {feat.get('bandwidth_hz', 0):>15,.1f} Hz (3dB channel)")
    clf_method = clf.get("method", "rule_based")
    clf_candidates = ", ".join(
        f"{c['label']}({c['score']:.0%})" for c in clf.get("candidates", [])[:3]
    )
    print(f"| Modulation        : {clf.get('modulation', 'Unknown')} ({clf.get('confidence', 0):.0%} via {clf_method})")
    print(f"|   Top candidates  : {clf_candidates or 'N/A'}")
    print(f"| Symbol Rate       : {sym.get('symbol_rate_hz', 0):>15,.1f} sym/s (SPS: {sym.get('samples_per_symbol', 'N/A')})")
    print(f"| Demodulation      : {dem.get('type', 'N/A')} ({dem.get('num_bits', 0)} raw bits)")
    print(f"| De-interleaving   : {intlv.get('pattern', 'None')} {intlv.get('best_params', '')}")
    print(f"| FEC Decoding      : {fec.get('method', 'None')} ({fec.get('decoded_count', 0)} bits decoded)")
    print(f"| Header Sync Match : {header_info}")
    print("+" + "-" * 70 + "+")
    if was_assumed:
        print("| [!] NOTICE: Sampling rate was not detected in metadata or filename.")
        print("|     Defaulted to 1.0 MHz. If capture was 4MHz or 6MHz, run with:")
        print("|     python run_pipeline.py --sample-rate 4M (or --sample-rate 6M)")
        print("+" + "-" * 70 + "+")
    print(f"Outputs written to: {os.path.abspath(output_dir)}/")
    print(f"  |-- {file_stem}_psd_spectrum.png")
    print(f"  |-- {file_stem}_spectrogram_waterfall.png")
    print(f"  |-- {file_stem}_constellation.png")
    print(f"  |-- {file_stem}_summary.txt")
    print(f"  |-- {file_stem}_report.json")
    if recovered_bits:
        print(f"  \\-- {file_stem}_payload.txt / .bin\n")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated Signal Parameter & Observation Extraction Pipeline")
    parser.add_argument("--input", "-i", help="Path to a single .iq or .wav signal file")
    parser.add_argument("--input-dir", default="input", help="Directory containing input .iq / .wav files (default: 'input')")
    parser.add_argument("--output-dir", "-o", default="output", help="Directory to store analysis outputs (default: 'output')")
    parser.add_argument("--sample-rate", "-fs", type=str, help="Explicit sampling rate (e.g. 4M, 4MHz, 4MSPS, 6M, 250k, 2000000)")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    target_files = []
    if args.input:
        target_files = [os.path.abspath(args.input)]
    else:
        os.makedirs(input_dir, exist_ok=True)
        patterns = [os.path.join(input_dir, "*.iq"), os.path.join(input_dir, "*.wav")]
        for p in patterns:
            target_files.extend(glob.glob(p))

        if not target_files:
            test_storage = os.path.join(BACKEND_DIR, "storage_test")
            if os.path.exists(test_storage):
                target_files.extend(glob.glob(os.path.join(test_storage, "*.iq")))
                target_files.extend(glob.glob(os.path.join(test_storage, "*.wav")))
            if target_files:
                print(f"[Notice] 'input/' is empty. Found {len(target_files)} test signal(s) in 'backend/storage_test/'.")
            else:
                print(f"No signal files found in '{input_dir}'.")
                print("Drop your .iq or .wav files into the 'input/' folder and re-run:")
                print("    python run_pipeline.py")
                return

    print(f"Starting Signal Parameter Extraction on {len(target_files)} file(s)...")
    all_results = []
    for fpath in target_files:
        try:
            res = analyze_single_file(fpath, output_dir, sample_rate_override=args.sample_rate)
            all_results.append(res)
        except Exception as err:
            print(f"[Error] Failed to process {fpath}: {err}")

    if all_results:
        dash_path = _generate_html_dashboard(all_results, output_dir)
        print(f"Interactive Dashboard generated: {dash_path}")


if __name__ == "__main__":
    main()
