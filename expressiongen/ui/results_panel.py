"""Results gallery — one tile per expression showing label, prompt and thumbnails."""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ..models import Expression


class ResultTile(QWidget):
    def __init__(self, expr: Expression, parent: QWidget | None = None):
        super().__init__(parent)
        self.label = expr.label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        title = QLabel(expr.label or "(unnamed)")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.prompt = QLabel(expr.prompt)
        self.prompt.setWordWrap(True)
        self.prompt.setMaximumHeight(60)
        self.prompt.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(self.prompt)

        self.thumbs = QGridLayout()
        self.thumbs.setSpacing(4)
        layout.addLayout(self.thumbs)
        layout.addStretch(1)

        self.setMinimumWidth(220)
        self.setStyleSheet("ResultTile { border: 1px solid #ccc; border-radius: 6px; }")

    def add_image(self, path: str) -> None:
        pm = QPixmap(path)
        if pm.isNull():
            return
        thumb = pm.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl = QLabel()
        lbl.setPixmap(thumb)
        lbl.setToolTip(os.path.basename(path))
        count = self.thumbs.count()
        self.thumbs.addWidget(lbl, count // 2, count % 2)

    def clear_images(self) -> None:
        while self.thumbs.count():
            item = self.thumbs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ResultsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(10)
        scroll.setWidget(self.grid_widget)
        outer.addWidget(scroll)
        self.tiles: dict[str, ResultTile] = {}

    def set_expressions(self, exprs: list[Expression]) -> None:
        self._clear()
        for i, e in enumerate(exprs):
            if not e.label:
                continue
            tile = ResultTile(e)
            self.tiles[e.label] = tile
            self.grid.addWidget(tile, i // 3, i % 3)

    def add_image(self, label: str, path: str) -> None:
        tile = self.tiles.get(label)
        if tile is not None:
            tile.add_image(path)

    def _clear(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tiles.clear()
