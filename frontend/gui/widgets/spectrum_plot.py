"""
spectrum_plot.py – Power Spectral Density (PSD) matplotlib canvas widget.

Embeds a matplotlib FigureCanvasQTAgg inside a PyQt6 QWidget and
provides an ``update(freqs, psd_db)`` method for live refresh.
"""
from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class SpectrumPlot(QWidget):
    """PSD spectrum plot widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fig   = Figure(tight_layout=True)
        self._ax    = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)

        self._ax.set_xlabel("Frequency (Hz)")
        self._ax.set_ylabel("Power (dBFS)")
        self._ax.set_title("Power Spectral Density")
        self._ax.grid(True, alpha=0.3)
        self._line, = self._ax.plot([], [], lw=1, color="steelblue")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

    def update(self, freqs: list | np.ndarray, psd_db: list | np.ndarray) -> None:
        """Refresh the plot with new frequency / PSD data.

        Args:
            freqs:  Frequency axis in Hz.
            psd_db: Power in dBFS (same length as freqs).
        """
        freqs  = np.asarray(freqs)
        psd_db = np.asarray(psd_db)
        self._line.set_data(freqs, psd_db)
        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()
