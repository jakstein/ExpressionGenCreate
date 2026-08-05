"""Main application window."""

from __future__ import annotations

import json
import os
import random

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from ..models import Preset
from ..presets import (
    list_presets,
    load_current,
    load_preset,
    save_current,
    save_preset,
)
from ..worker import GenerationWorker
from ..workflow_builder import build_api_graph
from .expression_panel import ExpressionPanel
from .global_panel import GlobalPanel
from .results_panel import ResultsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ExpressionGenCreate")
        self.resize(1280, 820)

        self.current_name = "Untitled"
        self.worker: GenerationWorker | None = None

        self._build_toolbar()

        self.global_panel = GlobalPanel()
        self.expression_panel = ExpressionPanel()
        self.results_panel = ResultsPanel()
        self.results_panel.regenerate_requested.connect(self.on_regenerate_image)

        self.left_split = QSplitter(Qt.Vertical)
        self.left_split.addWidget(self.global_panel)
        self.left_split.addWidget(self.expression_panel)
        self.left_split.setCollapsible(0, False)
        self.left_split.setCollapsible(1, False)
        self.left_split.setStretchFactor(0, 1)
        self.left_split.setStretchFactor(1, 1)

        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.addWidget(self.left_split)
        self.main_split.addWidget(self.results_panel)
        self.main_split.setStretchFactor(0, 2)
        self.main_split.setStretchFactor(1, 3)
        self.setCentralWidget(self.main_split)

        self._refresh_preset_combo()
        self._load_current_or_default()

    # -- setup -------------------------------------------------------------
    def _build_toolbar(self) -> None:
        tb = self.addToolBar("Main")
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.clicked.connect(self.on_run)
        self.interrupt_btn = QPushButton("■ Interrupt")
        self.interrupt_btn.setEnabled(False)
        self.interrupt_btn.clicked.connect(self.on_interrupt)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(160)
        self.preset_combo.setEditable(False)

        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.on_load_preset)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.on_save_preset)
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.on_new)
        export_btn = QPushButton("Export JSON")
        export_btn.clicked.connect(self.on_export)

        for w in (self.run_btn, self.interrupt_btn, QLabel(" Preset:"),
                  self.preset_combo, load_btn, save_btn, new_btn, export_btn):
            tb.addWidget(w)

    def _refresh_preset_combo(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(list_presets())
        self.preset_combo.blockSignals(False)

    def _load_current_or_default(self) -> None:
        preset = load_current()
        if preset is None:
            preset = Preset.default()
        self.apply_preset(preset)
        self.statusBar().showMessage("Ready.")

    # -- preset handling ---------------------------------------------------
    def collect_preset(self) -> Preset:
        return Preset(
            name=self.current_name,
            globals=self.global_panel.get_values(),
            expressions=self.expression_panel.get_expressions(),
        )

    def apply_preset(self, preset: Preset) -> None:
        self.current_name = preset.name
        self.global_panel.set_values(preset.globals)
        self.expression_panel.set_expressions(preset.expressions)
        idx = self.preset_combo.findText(preset.name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.results_panel.set_expressions(preset.expressions)

    def on_new(self) -> None:
        self.apply_preset(Preset.default())
        self.statusBar().showMessage("New blank preset.")

    def on_save_preset(self) -> None:
        preset = self.collect_preset()
        name, ok = QInputDialog.getText(
            self, "Save Preset", "Preset name:", text=preset.name
        )
        if not ok or not name.strip():
            return
        preset.name = name.strip()
        self.current_name = preset.name
        save_preset(preset, preset.name)
        self._refresh_preset_combo()
        idx = self.preset_combo.findText(preset.name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.statusBar().showMessage(f"Saved preset '{preset.name}'.")

    def on_load_preset(self) -> None:
        name = self.preset_combo.currentText()
        if not name:
            return
        try:
            preset = load_preset(name)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            QMessageBox.warning(self, "Load failed", str(exc))
            return
        self.apply_preset(preset)
        self.statusBar().showMessage(f"Loaded preset '{name}'.")

    def on_export(self) -> None:
        preset = self.collect_preset()
        graph, _ = build_api_graph(preset)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export workflow JSON", "workflow_api.json", "JSON (*.json)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        self.statusBar().showMessage(f"Exported API graph to {path}")

    # -- run ---------------------------------------------------------------
    def on_run(self) -> None:
        preset = self.collect_preset()
        save_current(preset)
        if not preset.expressions or not any(e.label for e in preset.expressions):
            QMessageBox.warning(
                self, "No expressions",
                "Add at least one expression with a non-empty label."
            )
            return
        self.results_panel.set_expressions(preset.expressions)

        self.worker = GenerationWorker(preset)
        self.worker.progress.connect(self.statusBar().showMessage)
        self.worker.log.connect(lambda m: print("[comfy]", m))
        self.worker.image_ready.connect(self.results_panel.add_image)
        self.worker.finished.connect(self.on_finished)
        self.run_btn.setEnabled(False)
        self.interrupt_btn.setEnabled(True)
        self.worker.start()

    def on_interrupt(self) -> None:
        if self.worker is not None:
            self.worker.request_interrupt()
            self.statusBar().showMessage("Interrupt requested...")

    def on_regenerate_image(self, label: str, path: str) -> None:
        """Regenerate a single expression's image with a fresh random seed.

        Runs the exact same workflow (globals + that expression's prompt) but
        with a randomized seed and a batch size of 1. The new image overwrites
        the clicked image in place, and the preview is updated.
        """
        if self.worker is not None and self.worker.isRunning():
            self.statusBar().showMessage("Generation already in progress.")
            return
        preset = self.collect_preset()
        expr = next((e for e in preset.expressions if e.label == label), None)
        if expr is None:
            return

        single = Preset(name=preset.name, globals=preset.globals, expressions=[expr])
        single.globals.seed = random.randint(0, 2**50)
        single.globals.seed_mode = "fixed"
        single.globals.count_per_item = 1

        self.worker = GenerationWorker(single, target_path=path or None)
        self.worker.progress.connect(self.statusBar().showMessage)
        self.worker.log.connect(lambda m: print("[comfy]", m))
        if path:
            self.worker.image_ready.connect(self.results_panel.replace_image)
        else:
            self.worker.image_ready.connect(self.results_panel.add_image)
        self.worker.finished.connect(self.on_finished)
        self.run_btn.setEnabled(False)
        self.interrupt_btn.setEnabled(True)
        self.worker.start()
        self.statusBar().showMessage(f"Regenerating '{label}' with a new seed...")

    def on_finished(self, success: bool, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.interrupt_btn.setEnabled(False)
        self.statusBar().showMessage(message)
        if not success:
            QMessageBox.critical(self, "Generation failed", message)

    # -- misc --------------------------------------------------------------
    def closeEvent(self, event) -> None:
        save_current(self.collect_preset())
        super().closeEvent(event)
