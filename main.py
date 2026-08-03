import sys

from expressiongen.ui.main_window import MainWindow


def main() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("ExpressionGenCreate")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
