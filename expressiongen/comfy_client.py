"""Thin client for a ComfyUI server running on :8188 (default).

HTTP (requests) is used for the standard API; the websocket is used to receive
each output node's results as soon as it finishes, so the caller can download
and display images progressively instead of waiting for the whole batch.
"""

from __future__ import annotations

import json
import time
import uuid

import requests
import websocket


class ComfyClient:
    def __init__(self, base_url: str, timeout: int = 1800):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.client_id = str(uuid.uuid4())
        self._client = None  # set by the worker once created

    def ping(self, timeout: float = 5.0) -> bool:
        try:
            r = self.session.get(self.base + "/", timeout=timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def queue_prompt(self, prompt_graph: dict) -> str:
        r = self.session.post(
            self.base + "/prompt",
            json={"prompt": prompt_graph, "client_id": self.client_id},
            timeout=60,
        )
        if r.status_code != 200:
            # Surface ComfyUI's validation errors (e.g. node_errors)
            try:
                detail = r.json()
            except ValueError:
                detail = r.text
            raise RuntimeError(f"ComfyUI rejected the workflow: {detail}")
        return r.json()["prompt_id"]

    def get_history(self, prompt_id: str, interval: float = 2.0):
        elapsed = 0.0
        while elapsed < self.timeout:
            try:
                r = self.session.get(
                    self.base + "/history/" + prompt_id, timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    if prompt_id in data:
                        return data[prompt_id]
            except requests.RequestException:
                pass
            time.sleep(interval)
            elapsed += interval
        raise TimeoutError(
            f"Timed out after {self.timeout}s waiting for ComfyUI prompt {prompt_id}"
        )

    def _ws_url(self) -> str:
        ws_base = self.base.replace("http://", "ws://", 1).replace(
            "https://", "wss://", 1
        )
        return f"{ws_base}/ws?clientId={self.client_id}"

    def stream_node_outputs(self, prompt_id: str, interval: float = 0.5):
        """Yield ``(node_id, output)`` as output nodes finish for ``prompt_id``.

        Blocks until ComfyUI reports the prompt is done (``execution_success``,
        ``execution_error``, ``execution_interrupted``, or a legacy
        ``executing`` with a null node). Each yielded ``output`` is the node's
        UI output dict, e.g. ``{"images": [{"filename", "subfolder", "type"}]}``
        for a SaveImage node, matching the shape found in ``/history``.

        The same ``client_id`` that queued the prompt must be used, otherwise
        ComfyUI will not route ``executed`` messages to this connection. If the
        websocket cannot be established or dies mid-stream this raises, so the
        caller can fall back to polling ``/history``.
        """
        ws = websocket.create_connection(self._ws_url(), timeout=15)
        try:
            elapsed = 0.0
            while elapsed < self.timeout:
                ws.settimeout(interval)
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    elapsed += interval
                    continue
                if not isinstance(raw, str):
                    continue
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if event.get("type") not in (
                    "executed",
                    "executing",
                    "execution_success",
                    "execution_error",
                    "execution_interrupted",
                ):
                    continue
                data = event.get("data") or {}
                if data.get("prompt_id") != prompt_id:
                    continue
                mtype = event["type"]
                if mtype == "executed":
                    node = data.get("node")
                    if node is not None:
                        yield node, data.get("output") or {}
                elif mtype == "executing":
                    if data.get("node") is None:
                        return
                else:
                    return
            raise TimeoutError(
                f"Timed out after {self.timeout}s waiting for ComfyUI prompt "
                f"{prompt_id}"
            )
        finally:
            ws.close()

    def get_image(self, filename: str, subfolder: str, type_: str) -> bytes:
        r = self.session.get(
            self.base + "/view",
            params={"filename": filename, "subfolder": subfolder, "type": type_},
            timeout=60,
        )
        r.raise_for_status()
        return r.content

    def interrupt(self) -> None:
        try:
            self.session.post(self.base + "/interrupt", timeout=10)
        except requests.RequestException:
            pass
