"""
analysis_tab.py – Spectrum, waterfall, and constellation viewer tab.

Displays three live views:
  - Power Spectral Density (spectrum plot)
  - Spectrogram / waterfall
  - IQ constellation diagram
"""
from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QMessageBox
from PyQt6.QtCore import Qt

from ..widgets.spectrum_plot import SpectrumPlot
from ..widgets.waterfall_plot import WaterfallPlot
from ..widgets.constellation_plot import ConstellationPlot


class AnalysisTab(QWidget):
    """Tab combining spectrum, waterfall, and constellation widgets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top splitter: spectrum | waterfall
        top_split = QSplitter(Qt.Orientation.Horizontal)
        self._spectrum     = SpectrumPlot(self)
        self._waterfall    = WaterfallPlot(self)
        top_split.addWidget(self._spectrum)
        top_split.addWidget(self._waterfall)
        top_split.setSizes([600, 600])

        # Bottom: constellation
        self._constellation = ConstellationPlot(self)

        main_split = QSplitter(Qt.Orientation.Vertical)
        main_split.addWidget(top_split)
        main_split.addWidget(self._constellation)
        main_split.setSizes([450, 350])

        layout.addWidget(main_split)

    # ── public API ────────────────────────────────────────────────────────────

    def load_file(self, path: str, overrides: dict | None = None) -> dict | None:
        """Load an IQ/WAV file, run analysis, and refresh all plots."""
        import requests

        payload = {"file_path": path}
        if overrides:
            if overrides.get("sample_rate"):
                payload["sample_rate_override"] = overrides["sample_rate"]
            if overrides.get("modulation") and overrides["modulation"] != "Auto":
                payload["modulation_override"] = overrides["modulation"]
            if overrides.get("symbol_rate"):
                payload["symbol_rate_override"] = overrides["symbol_rate"]
            if overrides.get("fec") and overrides["fec"] != "None":
                payload["fec_override"] = overrides["fec"]

        data = None
        try:
            resp = requests.post(
                "http://localhost:8000/analyze",
                json=payload,
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # Fallback to in-process execution if backend API is not running standalone
            try:
                from app.routers.analysis import _load_raw_file, _execute_full_pipeline
                from app.schemas import DirectAnalysisRequest
                sig, sr, _ = _load_raw_file(path)
                req = DirectAnalysisRequest(**payload)
                data = _execute_full_pipeline(sig, sr, req)
            except Exception as exc:
                QMessageBox.warning(self, "Analysis Error", f"Failed to analyze signal:\n{exc}")
                return None

        if not data:
            return None

        # 1. Update Spectrum Plot
        if "freqs" in data and "psd" in data:
            self._spectrum.update(
                freqs=data["freqs"],
                psd_db=data["psd"],
            )

        # 2. Update Waterfall Spectrogram
        if "spectrogram" in data and "power_db_matrix" in data["spectrogram"]:
            mat = np.array(data["spectrogram"]["power_db_matrix"]).T
            self._waterfall.update(mat)

        # 3. Update Constellation
        if "iq_samples" in data and "i" in data["iq_samples"] and "q" in data["iq_samples"]:
            i_arr = np.array(data["iq_samples"]["i"])
            q_arr = np.array(data["iq_samples"]["q"])
            iq = i_arr + 1j * q_arr
            self._constellation.update(iq)

        return data
