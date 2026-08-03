"""Expression editor — add/remove/reorder rows, each with a label + prompt."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from ..models import Expression


class ExpressionRow(QWidget):
    remove_requested = Signal(QWidget)
    move_requested = Signal(QWidget, int)  # +1 down, -1 up

    def __init__(self, expr: Expression | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        expr = expr or Expression()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label_edit = QLineEdit(expr.label)
        self.label_edit.setPlaceholderText("label e.g. laugh")
        self.label_edit.setMaximumWidth(140)

        self.prompt_edit = QTextEdit(expr.prompt)
        self.prompt_edit.setPlaceholderText("modifier prompt appended to the shared positive")
        self.prompt_edit.setMinimumHeight(46)
        self.prompt_edit.setMaximumHeight(90)

        up = QPushButton("↑")
        up.setMaximumWidth(28)
        up.clicked.connect(lambda: self.move_requested.emit(self, -1))
        down = QPushButton("↓")
        down.setMaximumWidth(28)
        down.clicked.connect(lambda: self.move_requested.emit(self, 1))
        rm = QPushButton("✕")
        rm.setMaximumWidth(28)
        rm.clicked.connect(lambda: self.remove_requested.emit(self))

        layout.addWidget(self.label_edit)
        layout.addWidget(self.prompt_edit, 1)
        layout.addWidget(up)
        layout.addWidget(down)
        layout.addWidget(rm)

    def values(self) -> Expression:
        return Expression(
            label=self.label_edit.text().strip(),
            prompt=self.prompt_edit.toPlainText().strip(),
        )


class ExpressionPanel(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("Expressions"))
        header.addStretch(1)
        add_btn = QPushButton("+ Add expression")
        add_btn.clicked.connect(self.add_row)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.list_widget = QWidget()
        self.rows_layout = QVBoxLayout(self.list_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)

    def add_row(self, expr: Expression | None = None) -> ExpressionRow:
        row = ExpressionRow(expr)
        row.remove_requested.connect(self._on_remove)
        row.move_requested.connect(self._on_move)
        self.rows_layout.addWidget(row)
        self.changed.emit()
        return row

    def _on_remove(self, row: QWidget) -> None:
        row.deleteLater()
        self.changed.emit()

    def _on_move(self, row: QWidget, direction: int) -> None:
        idx = self.rows_layout.indexOf(row)
        target = idx + direction
        if 0 <= target < self.rows_layout.count():
            self.rows_layout.removeWidget(row)
            self.rows_layout.insertWidget(target, row)
        self.changed.emit()

    def set_expressions(self, exprs: list[Expression]) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for e in exprs:
            self.add_row(e)

    def get_expressions(self) -> list[Expression]:
        out = []
        for i in range(self.rows_layout.count()):
            w = self.rows_layout.itemAt(i).widget()
            if isinstance(w, ExpressionRow):
                out.append(w.values())
        return out
