"""
test_gui.py – Smoke tests for the frontend GUI layer.

These tests use PyQt6's QTest utilities and do NOT require a display
when run with ``QT_QPA_PLATFORM=offscreen``.
"""
import os
import sys
import pytest

# Force offscreen rendering for CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_main_window_creates(qt_app):
    from gui.main_window import MainWindow
    win = MainWindow()
    assert win is not None
    win.close()


def test_tab_count(qt_app):
    from gui.main_window import MainWindow
    win = MainWindow()
    assert win._tabs.count() == 3
    win.close()


def test_tab_titles(qt_app):
    from gui.main_window import MainWindow
    win = MainWindow()
    titles = [win._tabs.tabText(i) for i in range(win._tabs.count())]
    assert "Analysis"   in titles
    assert "Parameters" in titles
    assert "Pipeline"   in titles
    win.close()


def test_spectrum_plot_update(qt_app):
    import numpy as np
    from gui.widgets.spectrum_plot import SpectrumPlot
    w = SpectrumPlot()
    freqs  = np.linspace(-1e6, 1e6, 512)
    psd_db = -30 * np.ones(512)
    w.update(freqs, psd_db)          # should not raise


def test_waterfall_plot_update(qt_app):
    import numpy as np
    from gui.widgets.waterfall_plot import WaterfallPlot
    w = WaterfallPlot()
    spec = np.random.uniform(-80, 0, size=(10, 256))
    w.update(spec)                   # should not raise


def test_constellation_plot_update(qt_app):
    import numpy as np
    from gui.widgets.constellation_plot import ConstellationPlot
    w = ConstellationPlot()
    iq = np.random.randn(1000) + 1j * np.random.randn(1000)
    w.update(iq.astype(np.complex64))  # should not raise


def test_parameters_tab_get(qt_app):
    from gui.tabs.parameters_tab import ParametersTab
    tab = ParametersTab()
    params = tab.get_parameters()
    assert "modulation"    in params
    assert "sample_rate"   in params
    assert "symbol_rate"   in params
    assert "fec"           in params
