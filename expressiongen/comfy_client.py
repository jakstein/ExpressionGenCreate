"""Thin requests-based client for a ComfyUI server running on :8188 (default)."""

from __future__ import annotations

import time
import uuid

import requests


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
