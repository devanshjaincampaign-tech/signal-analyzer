"""
parameters_tab.py – Editable override fields for signal parameters.

Allows the operator to manually specify or override auto-detected values:
  - Center frequency, sample rate, modulation type
  - Symbol rate, FEC scheme, interleave depth
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox, QVBoxLayout,
)


class ParametersTab(QWidget):
    """Tab for manually editing signal analysis parameters."""

    MOD_TYPES = ["Auto", "BPSK", "QPSK", "8PSK", "16QAM", "64QAM", "2FSK", "4FSK"]
    FEC_TYPES  = ["None", "Viterbi R=1/2 K=7", "Reed-Solomon (255,223)",
                  "LDPC DVB-S2", "Concatenated RS+Viterbi"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # ── Signal parameters ──────────────────────────────────────────────
        sig_box   = QGroupBox("Signal Parameters")
        sig_form  = QFormLayout(sig_box)

        self._center_freq = QDoubleSpinBox()
        self._center_freq.setRange(0, 6e9)
        self._center_freq.setSuffix(" Hz")
        self._center_freq.setDecimals(0)
        sig_form.addRow("Center frequency:", self._center_freq)

        self._sample_rate = QDoubleSpinBox()
        self._sample_rate.setRange(1e3, 500e6)
        self._sample_rate.setSuffix(" sps")
        self._sample_rate.setDecimals(0)
        sig_form.addRow("Sample rate:", self._sample_rate)

        self._mod_type = QComboBox()
        self._mod_type.addItems(self.MOD_TYPES)
        sig_form.addRow("Modulation:", self._mod_type)

        self._symbol_rate = QDoubleSpinBox()
        self._symbol_rate.setRange(100, 100e6)
        self._symbol_rate.setSuffix(" sym/s")
        self._symbol_rate.setDecimals(0)
        sig_form.addRow("Symbol rate:", self._symbol_rate)

        # ── FEC / interleave ───────────────────────────────────────────────
        fec_box  = QGroupBox("FEC & Interleaving")
        fec_form = QFormLayout(fec_box)

        self._fec_type = QComboBox()
        self._fec_type.addItems(self.FEC_TYPES)
        fec_form.addRow("FEC scheme:", self._fec_type)

        self._interleave_depth = QSpinBox()
        self._interleave_depth.setRange(0, 256)
        self._interleave_depth.setSpecialValueText("Auto")
        fec_form.addRow("Interleave depth:", self._interleave_depth)

        # ── Actions ───────────────────────────────────────────────────────
        self._apply_btn = QPushButton("Apply Overrides")
        self._apply_btn.clicked.connect(self._on_apply)

        self._reset_btn = QPushButton("Reset to Auto-Detected")
        self._reset_btn.clicked.connect(self._on_reset)

        outer.addWidget(sig_box)
        outer.addWidget(fec_box)
        outer.addWidget(self._apply_btn)
        outer.addWidget(self._reset_btn)
        outer.addStretch()

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_apply(self) -> None:
        params = self.get_parameters()
        # TODO: signal to pipeline tab / backend
        print("Applying parameters:", params)

    def _on_reset(self) -> None:
        self._mod_type.setCurrentIndex(0)       # Auto
        self._fec_type.setCurrentIndex(0)       # None
        self._interleave_depth.setValue(0)      # Auto

    def get_parameters(self) -> dict:
        return {
            "center_frequency": self._center_freq.value(),
            "sample_rate":      self._sample_rate.value(),
            "modulation":       self._mod_type.currentText(),
            "symbol_rate":      self._symbol_rate.value(),
            "fec":              self._fec_type.currentText(),
            "interleave_depth": self._interleave_depth.value(),
        }
