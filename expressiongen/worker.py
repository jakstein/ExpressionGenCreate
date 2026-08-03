"""Background worker that submits the workflow to ComfyUI, waits for results,
downloads the generated images, and writes them to disk."""

from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import QThread, Signal

from .comfy_client import ComfyClient
from .models import Preset
from .paths import _app_dir
from .workflow_builder import build_api_graph


class GenerationWorker(QThread):
    progress = Signal(str)          # status-bar text
    image_ready = Signal(str, str)  # label, local file path
    finished = Signal(bool, str)    # success, message
    log = Signal(str)               # detailed log line

    def __init__(self, preset: Preset):
        super().__init__()
        self.preset = preset
        self._client: ComfyClient | None = None

    def request_interrupt(self) -> None:
        if self._client is not None:
            self._client.interrupt()

    def run(self) -> None:
        try:
            g = self.preset.globals
            self._client = ComfyClient(g.comfy_url)
            if not self._client.ping():
                self.finished.emit(
                    False, f"ComfyUI not reachable at {g.comfy_url}"
                )
                return

            graph, save_map = build_api_graph(self.preset)
            self.progress.emit(
                f"Submitting workflow ({len(self.preset.expressions)} expressions)..."
            )
            self.log.emit(f"Graph has {len(graph)} nodes.")

            prompt_id = self._client.queue_prompt(graph)
            self.progress.emit(f"Queued (id={prompt_id[:8]}). Generating...")

            hist = self._client.get_history(prompt_id)

            status = hist.get("status", {})
            if status.get("status_str") == "error":
                msg = status.get("exception_message") or "ComfyUI execution error"
                node_errors = status.get("node_errors")
                if node_errors:
                    msg += f"\n{node_errors}"
                self.finished.emit(False, msg)
                return

            outputs = hist.get("outputs", {})
            # Resolve relative output_base relative to the app directory
            # so it works both in development and when packaged.
            out_base = g.output_base
            if not os.path.isabs(out_base):
                out_base = os.path.join(_app_dir(), out_base)
            outdir = os.path.join(out_base, *g.character_folder.split("/"))
            os.makedirs(outdir, exist_ok=True)

            total = 0
            for node_id, label in save_map.items():
                for i, im in enumerate(outputs.get(node_id, {}).get("images", [])):
                    data = self._client.get_image(
                        im["filename"], im["subfolder"], im["type"]
                    )
                    fname = f"{label}.png" if len(
                        outputs.get(node_id, {}).get("images", [])
                    ) == 1 else f"{label}_{i + 1:02d}.png"
                    fpath = os.path.join(outdir, fname)
                    with open(fpath, "wb") as fh:
                        fh.write(data)
                    self.image_ready.emit(label, fpath)
                    total += 1
                    self.log.emit(f"Saved {fpath}")

            self.finished.emit(
                True, f"Done. {total} image(s) saved to {outdir}"
            )
        except Exception as exc:  # noqa: BLE001 - surface anything to the UI
            self.log.emit(traceback.format_exc())
            self.finished.emit(False, str(exc))
