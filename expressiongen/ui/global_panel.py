"""Global settings panel — all shared parameters for the workflow."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..models import GlobalSettings

WEIGHT_DTYPES = ["default", "fp16", "fp8_e4m3fn", "fp8_e5m2", "bf16"]
CLIP_TYPES = ["stable_diffusion", "sd3", "sdxl", "flux", "ltxv", "pixart", "hunyuan_video"]
SAMPLERS = [
    "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_3m_sde",
    "dpmpp_sde", "ddim", "uni_pc", "lcm", "heun", "deis", "ddpm",
]
SCHEDULERS = [
    "simple", "normal", "karras", "ddim_uniform", "sgm_uniform",
    "exponential", "beta", "linear_quadratic", "kl_optimal",
]
UPSCALE_METHODS = ["lanczos", "bilinear", "bicubic", "nearest-exact"]
SEED_MODES = ["fixed", "randomize", "increment"]


class GlobalPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.w: dict[str, QWidget] = {}
        self._g = GlobalSettings()
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self._rebuild()

    # -- field helpers -----------------------------------------------------
    def _line(self, key: str, layout: QFormLayout, label: str, text: str = "") -> QLineEdit:
        le = QLineEdit(text)
        self.w[key] = le
        layout.addRow(label, le)
        return le

    def _int(self, key: str, layout: QFormLayout, label: str, val: int,
             minimum: int = 1, maximum: int = 2_147_483_647) -> QSpinBox:
        sb = QSpinBox()
        sb.setRange(minimum, maximum)
        sb.setValue(val)
        self.w[key] = sb
        layout.addRow(label, sb)
        return sb

    def _big_int(self, key: str, layout: QFormLayout, label: str, val: int) -> QLineEdit:
        le = QLineEdit(str(val))
        self.w[key] = le
        layout.addRow(label, le)
        return le

    def _double(self, key: str, layout: QFormLayout, label: str, val: float,
                step: float = 0.1, minimum: float = 0.0, maximum: float = 1000.0) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(minimum, maximum)
        sb.setSingleStep(step)
        sb.setValue(val)
        self.w[key] = sb
        layout.addRow(label, sb)
        return sb

    def _combo(self, key: str, layout: QFormLayout, label: str, options: list,
               val: str) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        cb.addItems(options)
        cb.setCurrentText(val)
        self.w[key] = cb
        layout.addRow(label, cb)
        return cb

    def _check(self, key: str, layout: QFormLayout, label: str, val: bool) -> QCheckBox:
        cb = QCheckBox()
        cb.setChecked(val)
        self.w[key] = cb
        layout.addRow(label, cb)
        return cb

    def _text(self, key: str, layout: QFormLayout, label: str, text: str) -> QPlainTextEdit:
        te = QPlainTextEdit(text)
        te.setMinimumHeight(90)
        self.w[key] = te
        layout.addRow(label, te)
        return te

    # -- groups ------------------------------------------------------------
    def _model_group(self) -> QGroupBox:
        box = QGroupBox("Model / Encoder / VAE")
        fl = QFormLayout(box)
        g = self._g
        self._line("model_name", fl, "Checkpoint", g.model_name)
        self._combo("weight_dtype", fl, "Weight dtype", WEIGHT_DTYPES, g.weight_dtype)
        self._line("clip_name", fl, "CLIP", g.clip_name)
        self._combo("clip_type", fl, "CLIP type", CLIP_TYPES, g.clip_type)
        self._line("vae_name", fl, "VAE", g.vae_name)
        self._double("model_shift", fl, "ModelSampling shift (AuraFlow)", g.model_shift)

        lorabox = QGroupBox("LoRA Stack — type name, 'None' disables")
        lf = QFormLayout(lorabox)
        for i in range(4):
            name, strength = g.loras[i]
            row = QHBoxLayout()
            name_le = QLineEdit(name)
            str_sb = QDoubleSpinBox()
            str_sb.setRange(-10.0, 10.0)
            str_sb.setSingleStep(0.05)
            str_sb.setValue(float(strength))
            row.addWidget(QLabel("Name:"))
            row.addWidget(name_le, 3)
            row.addWidget(QLabel("Strength:"))
            row.addWidget(str_sb, 1)
            lf.addRow(f"LoRA {i + 1}", row)
            self.w[f"lora_{i}_name"] = name_le
            self.w[f"lora_{i}_strength"] = str_sb
        fl.addRow(lorabox)
        return box

    def _resolution_group(self) -> QGroupBox:
        box = QGroupBox("Resolution / Batching")
        fl = QFormLayout(box)
        g = self._g
        self._int("width", fl, "Width", g.width, 64, 8192)
        self._int("height", fl, "Height", g.height, 64, 8192)
        self._int("count_per_item", fl, "Count per item (batch)", g.count_per_item, 1, 64)
        self._big_int("seed", fl, "Seed (base)", g.seed)
        self._combo("seed_mode", fl, "Seed mode", SEED_MODES, g.seed_mode)
        return box

    def _sampling_group(self) -> QGroupBox:
        box = QGroupBox("Sampling (KSampler Config)")
        fl = QFormLayout(box)
        g = self._g
        self._int("steps", fl, "Steps", g.steps, 1, 200)
        self._int("refiner_step", fl, "Refiner step", g.refiner_step, 0, 200)
        self._double("cfg", fl, "CFG", g.cfg, 0.1, 0.0, 100.0)
        self._combo("sampler_name", fl, "Sampler", SAMPLERS, g.sampler_name)
        self._combo("scheduler", fl, "Scheduler", SCHEDULERS, g.scheduler)
        self._double("denoise", fl, "Denoise", g.denoise, 0.05, 0.0, 1.0)
        return box

    def _prompts_group(self) -> QGroupBox:
        box = QGroupBox("Prompts")
        fl = QFormLayout(box)
        g = self._g
        self._text("positive_prompt", fl, "Positive (shared)", g.positive_prompt)
        self._text("negative_prompt", fl, "Negative", g.negative_prompt)
        self._line("pose_strength", fl, "Pose/action strength", g.pose_strength)
        return box

    def _output_group(self) -> QGroupBox:
        box = QGroupBox("Output / Files / Connection")
        fl = QFormLayout(box)
        g = self._g
        self._line("character_folder", fl, "Character folder (name+custom)", g.character_folder)
        self._check("remove_background", fl, "Remove background (BiRefNet)", g.remove_background)
        self._line("birefnet_model", fl, "BiRefNet model", g.birefnet_model)
        self._combo("upscale_method", fl, "Upscale method", UPSCALE_METHODS, g.upscale_method)
        self._double("upscale_factor", fl, "Upscale factor", g.upscale_factor, 0.1, 0.1, 8.0)
        self._line("comfy_url", fl, "ComfyUI URL", g.comfy_url)
        self._line("output_base", fl, "Local output base dir", g.output_base)
        return box

    # -- public API --------------------------------------------------------
    def set_values(self, g: GlobalSettings) -> None:
        self._g = g
        self._rebuild()

    def _rebuild(self) -> None:
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.w.clear()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setSpacing(10)
        v.addWidget(self._model_group())
        v.addWidget(self._resolution_group())
        v.addWidget(self._sampling_group())
        v.addWidget(self._prompts_group())
        v.addWidget(self._output_group())
        v.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def get_values(self) -> GlobalSettings:
        loras = []
        for i in range(4):
            name = self.w[f"lora_{i}_name"].text().strip() or "None"
            strength = self.w[f"lora_{i}_strength"].value()
            loras.append((name, strength))
        try:
            seed = int(self.w["seed"].text())
        except ValueError:
            seed = 0
        return GlobalSettings(
            model_name=self.w["model_name"].text(),
            weight_dtype=self.w["weight_dtype"].currentText(),
            clip_name=self.w["clip_name"].text(),
            clip_type=self.w["clip_type"].currentText(),
            vae_name=self.w["vae_name"].text(),
            model_shift=self.w["model_shift"].value(),
            loras=loras,
            width=self.w["width"].value(),
            height=self.w["height"].value(),
            count_per_item=self.w["count_per_item"].value(),
            seed=seed,
            seed_mode=self.w["seed_mode"].currentText(),
            steps=self.w["steps"].value(),
            refiner_step=self.w["refiner_step"].value(),
            cfg=self.w["cfg"].value(),
            sampler_name=self.w["sampler_name"].currentText(),
            scheduler=self.w["scheduler"].currentText(),
            denoise=self.w["denoise"].value(),
            negative_prompt=self.w["negative_prompt"].toPlainText(),
            positive_prompt=self.w["positive_prompt"].toPlainText(),
            pose_strength=self.w["pose_strength"].text(),
            character_folder=self.w["character_folder"].text(),
            remove_background=self.w["remove_background"].isChecked(),
            birefnet_model=self.w["birefnet_model"].text(),
            upscale_method=self.w["upscale_method"].currentText(),
            upscale_factor=self.w["upscale_factor"].value(),
            comfy_url=self.w["comfy_url"].text(),
            output_base=self.w["output_base"].text(),
        )
