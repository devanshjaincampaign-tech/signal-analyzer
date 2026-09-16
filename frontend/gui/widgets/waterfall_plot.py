"""
waterfall_plot.py – Spectrogram / waterfall matplotlib canvas widget.

Displays an STFT spectrogram as a scrolling heatmap (waterfall).
The ``update(spectrogram)`` method accepts a 2-D power array
(time × frequency, in dBFS) and refreshes the display.
"""
from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class WaterfallPlot(QWidget):
    """Scrolling spectrogram (waterfall) widget."""

    def __init__(self, parent: QWidget | None = None, history: int = 200) -> None:
        super().__init__(parent)
        self._history = history

        self._fig    = Figure(tight_layout=True)
        self._ax     = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)

        self._ax.set_xlabel("Frequency bin")
        self._ax.set_ylabel("Time (frames)")
        self._ax.set_title("Spectrogram / Waterfall")

        # Placeholder image
        self._data = np.full((history, 256), -80.0)
        self._img  = self._ax.imshow(
            self._data,
            aspect="auto",
            origin="upper",
            cmap="inferno",
            vmin=-80,
            vmax=0,
            interpolation="nearest",
        )
        self._fig.colorbar(self._img, ax=self._ax, label="dBFS")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

    def update(self, spectrogram: np.ndarray) -> None:
        """Append new spectrogram rows and refresh display.

        Args:
            spectrogram: 2-D array (n_frames × n_freqs) in dBFS.
        """
        spectrogram = np.asarray(spectrogram)
        n_new = spectrogram.shape[0]
        self._data = np.roll(self._data, -n_new, axis=0)
        self._data[-n_new:, : spectrogram.shape[1]] = spectrogram
        self._img.set_data(self._data)
        self._canvas.draw_idle()
