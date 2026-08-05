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
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from ..models import Expression


class _Clickable(QLabel):
    """QLabel that emits ``clicked`` on a left mouse-button release."""

    clicked = Signal()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ResultTile(QWidget):
    # Emitted with (expression label, image path) when an element is clicked.
    # The image path is "" when the tile has no generated image yet.
    clicked = Signal(str, str)

    def __init__(self, expr: Expression, parent: QWidget | None = None):
        super().__init__(parent)
        self.label = expr.label
        self.image_paths: list[str] = []
        self.thumb_labels: list[QLabel] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        title = _Clickable(expr.label or "(unnamed)")
        title.setStyleSheet("font-weight: bold;")
        title.setCursor(Qt.PointingHandCursor)
        title.clicked.connect(self._emit_click)
        layout.addWidget(title)

        self.prompt = _Clickable(expr.prompt)
        self.prompt.setWordWrap(True)
        self.prompt.setMaximumHeight(60)
        self.prompt.setStyleSheet("color: #555; font-size: 11px;")
        self.prompt.setCursor(Qt.PointingHandCursor)
        self.prompt.clicked.connect(self._emit_click)
        layout.addWidget(self.prompt)

        self.thumbs = QGridLayout()
        self.thumbs.setSpacing(4)
        layout.addLayout(self.thumbs)
        layout.addStretch(1)

        self.setMinimumWidth(220)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("ResultTile { border: 1px solid #ccc; border-radius: 6px; }")

    def _emit_click(self) -> None:
        self.clicked.emit(self.label, self.image_paths[0] if self.image_paths else "")

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._emit_click()
        super().mouseReleaseEvent(event)

    def add_image(self, path: str) -> None:
        pm = QPixmap(path)
        if pm.isNull():
            return
        thumb = pm.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl = _Clickable()
        lbl.setPixmap(thumb)
        lbl.setToolTip(os.path.basename(path))
        lbl.setCursor(Qt.PointingHandCursor)
        count = self.thumbs.count()
        self.thumbs.addWidget(lbl, count // 2, count % 2)
        self.image_paths.append(path)
        self.thumb_labels.append(lbl)
        lbl.clicked.connect(lambda p=path: self.clicked.emit(self.label, p))

    def replace_image(self, path: str) -> None:
        """Reload the thumbnail at ``path`` (which was overwritten in place)."""
        if path not in self.image_paths:
            return
        pm = QPixmap(path)
        if pm.isNull():
            return
        thumb = pm.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.thumb_labels[self.image_paths.index(path)].setPixmap(thumb)

    def clear_images(self) -> None:
        while self.thumbs.count():
            item = self.thumbs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.image_paths.clear()
        self.thumb_labels.clear()


class ResultsPanel(QWidget):
    regenerate_requested = Signal(str, str)  # expression label, image path

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
            tile.clicked.connect(self.regenerate_requested)
            self.tiles[e.label] = tile
            self.grid.addWidget(tile, i // 3, i % 3)

    def add_image(self, label: str, path: str) -> None:
        tile = self.tiles.get(label)
        if tile is not None:
            tile.add_image(path)

    def replace_image(self, label: str, path: str) -> None:
        tile = self.tiles.get(label)
        if tile is not None:
            tile.replace_image(path)

    def _clear(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tiles.clear()
