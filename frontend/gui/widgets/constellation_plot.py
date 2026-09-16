"""
constellation_plot.py – IQ constellation diagram matplotlib canvas widget.

Plots complex IQ samples as a scatter diagram.
The ``update(iq_samples)`` method accepts a 1-D complex numpy array
and refreshes the scatter plot in-place for low-latency live display.
"""
from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ConstellationPlot(QWidget):
    """IQ constellation scatter plot widget."""

    def __init__(self, parent: QWidget | None = None, max_points: int = 4096) -> None:
        super().__init__(parent)
        self._max_points = max_points

        self._fig    = Figure(tight_layout=True)
        self._ax     = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)

        self._ax.set_xlabel("In-phase (I)")
        self._ax.set_ylabel("Quadrature (Q)")
        self._ax.set_title("IQ Constellation")
        self._ax.set_aspect("equal")
        self._ax.grid(True, alpha=0.3)
        self._ax.axhline(0, color="gray", lw=0.5)
        self._ax.axvline(0, color="gray", lw=0.5)

        self._scatter = self._ax.scatter([], [], s=2, alpha=0.5, color="steelblue")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

    def update(self, iq_samples: np.ndarray) -> None:
        """Refresh the constellation with new IQ samples.

        Args:
            iq_samples: 1-D complex numpy array of IQ samples.
        """
        iq = np.asarray(iq_samples, dtype=np.complex64)
        if len(iq) > self._max_points:
            iq = iq[-self._max_points:]

        xy = np.column_stack([iq.real, iq.imag])
        self._scatter.set_offsets(xy)
        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()
