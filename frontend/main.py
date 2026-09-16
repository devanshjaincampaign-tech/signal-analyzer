"""
main.py – Entry point for the Signal Analyzer desktop GUI.

Launches the PyQt6 application and shows the main window.
"""
import sys

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Signal Analyzer")
    app.setOrganizationName("signal-analyzer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
