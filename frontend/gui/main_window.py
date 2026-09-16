"""
main_window.py – Top-level application window.

Hosts a QTabWidget containing:
  - Analysis Tab   (spectrum / waterfall / constellation views)
  - Parameters Tab (editable override fields)
  - Pipeline Tab   (stage-by-stage run/inspect controls)
"""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QToolBar, QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from .tabs.analysis_tab import AnalysisTab
from .tabs.parameters_tab import ParametersTab
from .tabs.pipeline_tab import PipelineTab


class MainWindow(QMainWindow):
    """Signal Analyzer main application window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Signal Analyzer - Spectral, Demod, FEC & Interleaving Tool")
        self.resize(1360, 860)
        self._current_file: str | None = None

        self._build_menu()
        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()

    # ── construction helpers ──────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_action = QAction("&Open signal file…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        analysis_menu = menu.addMenu("&Analysis")
        run_action = QAction("&Run Full Pipeline", self)
        run_action.setShortcut("Ctrl+R")
        run_action.triggered.connect(self._on_run_pipeline)
        analysis_menu.addAction(run_action)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main toolbar")
        tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        open_action = QAction("Open Signal (.iq / .wav)", self)
        open_action.triggered.connect(self._on_open_file)
        tb.addAction(open_action)

        run_action = QAction("Run Pipeline", self)
        run_action.triggered.connect(self._on_run_pipeline)
        tb.addAction(run_action)

    def _build_central_widget(self) -> None:
        self._tabs = QTabWidget()

        self._analysis_tab   = AnalysisTab(self)
        self._parameters_tab = ParametersTab(self)
        self._pipeline_tab   = PipelineTab(self)

        self._tabs.addTab(self._analysis_tab,   "Signal Visualizer")
        self._tabs.addTab(self._parameters_tab, "Parameter Overrides")
        self._tabs.addTab(self._pipeline_tab,   "Pipeline Inspector")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)
        self.setCentralWidget(container)

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready. Open a .iq or .wav signal file to begin.")

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open signal file",
            "",
            "Signal files (*.iq *.wav *.sigmf-meta);;All files (*)",
        )
        if path:
            self._current_file = path
            self._pipeline_tab.set_current_file(path)
            self._status.showMessage(f"Loaded signal: {path}")
            
            overrides = self._parameters_tab.get_parameters()
            data = self._analysis_tab.load_file(path, overrides=overrides)
            if data and "classification" in data:
                mod = data["classification"].get("modulation", "Unknown")
                sr = data.get("symbol_rate", {}).get("symbol_rate_hz", 0)
                self._status.showMessage(
                    f"Analyzed: {path} | Modulation: {mod} | Symbol Rate: {sr:,.0f} sym/s"
                )

    def _on_run_pipeline(self) -> None:
        if not self._current_file:
            self._on_open_file()
            return
        self._tabs.setCurrentWidget(self._pipeline_tab)
        self._pipeline_tab._on_run_all()
