"""
pipeline_tab.py – Stage-by-stage pipeline run and inspect controls.

Shows each processing stage as a row:
  Load → Preprocess → Spectral → Symbol Rate → Mod Classify
       → Demod → De-interleave → FEC → Correlate

Each stage has an individual Run button and a collapsible output inspector.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt


_STAGES = [
    ("Load",          "Ingest and validate .iq / .wav / .sigmf-meta file format"),
    ("Preprocess",    "DC offset removal, polyphase resampling, Hilbert analytic conversion"),
    ("Spectral",      "Power Spectral Density, waterfall spectrogram, occupied bandwidth"),
    ("Symbol Rate",   "Transition autocorrelation symbol rate and timing estimation"),
    ("Mod Classify",  "Cumulant-based C42 & phase variance modulation classification"),
    ("Demod",         "Demodulate BPSK, QPSK, 8-PSK, FSK, 16-QAM, 64-QAM constellations"),
    ("De-interleave", "Brute-force Block, Convolutional, Diagonal, Pseudo-Random de-interleaving"),
    ("FEC",           "Viterbi K=7 R=1/2, Reed-Solomon (255,223), LDPC BP, Concatenated decoding"),
    ("Correlate",     "Barker & CCSDS ASM sync-word correlation / Hamming search"),
]


class StageRow(QGroupBox):
    """Widget representing one pipeline stage with run button and collapsible inspector."""

    def __init__(self, name: str, description: str, run_handler: Optional[Callable[[str], Any]] = None, parent: QWidget | None = None) -> None:
        super().__init__(name, parent)
        self._name = name
        self._run_handler = run_handler

        layout = QHBoxLayout(self)

        self._desc  = QLabel(description)
        self._desc.setWordWrap(True)
        self._desc.setMaximumWidth(380)

        self._run_btn    = QPushButton("Run")
        self._run_btn.setFixedWidth(70)
        self._run_btn.clicked.connect(self._on_run)

        self._status_lbl = QLabel("Idle")
        self._status_lbl.setFixedWidth(80)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._inspect_btn = QPushButton("Inspect ▾")
        self._inspect_btn.setCheckable(True)
        self._inspect_btn.setFixedWidth(80)
        self._inspect_btn.toggled.connect(self._toggle_output)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFixedHeight(120)
        self._output.hide()

        right = QVBoxLayout()
        controls = QHBoxLayout()
        controls.addWidget(self._run_btn)
        controls.addWidget(self._status_lbl)
        controls.addWidget(self._inspect_btn)
        right.addLayout(controls)
        right.addWidget(self._output)

        layout.addWidget(self._desc, stretch=1)
        layout.addLayout(right)

    def set_status(self, text: str, color: str = "black") -> None:
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

    def set_output(self, data: Any) -> None:
        if isinstance(data, (dict, list)):
            self._output.setText(json.dumps(data, indent=2))
        else:
            self._output.setText(str(data))

    def _on_run(self) -> None:
        self.set_status("Running…", "orange")
        if self._run_handler:
            try:
                res = self._run_handler(self._name)
                self.set_output(res)
                self.set_status("Done ✓", "green")
            except Exception as e:
                self.set_status("Error ✗", "red")
                self._output.setText(f"Error executing stage {self._name}:\n{e}")
        else:
            self.set_status("Done ✓", "green")
            self._output.append(f"[{self._name}] completed.")

    def _toggle_output(self, checked: bool) -> None:
        self._output.setVisible(checked)
        self._inspect_btn.setText("Inspect ▴" if checked else "Inspect ▾")


class PipelineTab(QWidget):
    """Tab providing per-stage run and inspect controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_file: Optional[str] = None
        self._pipeline_results: dict = {}
        self._build_ui()

    def set_current_file(self, file_path: str) -> None:
        self._current_file = file_path

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # Top bar with Run All button
        top_bar = QHBoxLayout()
        self._run_all_btn = QPushButton("▶  Run Full Pipeline")
        self._run_all_btn.setFixedHeight(36)
        self._run_all_btn.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        self._run_all_btn.clicked.connect(self._on_run_all)
        top_bar.addWidget(self._run_all_btn)
        top_bar.addStretch()
        outer.addLayout(top_bar)

        # Scrollable stage list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        stage_layout = QVBoxLayout(container)
        stage_layout.setSpacing(6)

        self._stage_rows: dict[str, StageRow] = {}
        for name, desc in _STAGES:
            row = StageRow(name, desc, run_handler=self._execute_stage, parent=self)
            self._stage_rows[name] = row
            stage_layout.addWidget(row)

        stage_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _execute_stage(self, stage_name: str) -> Any:
        if not self._current_file:
            raise ValueError("No signal file loaded. Please open a file via File > Open.")

        import requests
        try:
            resp = requests.post(
                "http://localhost:8000/analyze",
                json={"file_path": self._current_file},
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            self._pipeline_results = data
        except Exception:
            # Fallback to local execution if backend API server is offline
            from app.routers.analysis import _load_raw_file, _execute_full_pipeline
            sig, sr, _ = _load_raw_file(self._current_file)
            data = _execute_full_pipeline(sig, sr)
            self._pipeline_results = data

        stage_key_map = {
            "Load": lambda d: {"file": self._current_file, "status": "loaded"},
            "Preprocess": lambda d: {"status": "DC removed, normalized to unit RMS"},
            "Spectral": lambda d: d.get("features"),
            "Symbol Rate": lambda d: d.get("symbol_rate"),
            "Mod Classify": lambda d: d.get("classification"),
            "Demod": lambda d: d.get("demod"),
            "De-interleave": lambda d: d.get("interleaving"),
            "FEC": lambda d: d.get("fec"),
            "Correlate": lambda d: d.get("correlation"),
        }

        extractor = stage_key_map.get(stage_name, lambda d: d)
        return extractor(self._pipeline_results)

    def _on_run_all(self) -> None:
        if not self._current_file:
            QMessageBox.warning(self, "No File", "Please open a .iq or .wav file first.")
            return

        for name, row in self._stage_rows.items():
            row._on_run()
