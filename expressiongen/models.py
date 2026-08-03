"""Data model for ExpressionGenCreate presets.

A Preset is split into global settings (shared by every expression) and a list
of expressions. Each expression only carries a label (used for the filename and
the result tile) and a prompt (the "modifier" appended to the shared positive
prompt, exactly like the Anima reference workflow).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


# Default prompts copied from the reference Anima_Full_Body workflow so a fresh
# install produces something usable out of the box.
DEFAULT_NEGATIVE = (
    "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, "
    "jpeg artifacts, chromatic aberration, different character, changed outfit, "
    "changed hairstyle, changed hair colour, changed eye colour, changed accessories, "
    "duplicate character, multiple people, extra people, extra limbs, missing limbs, "
    "malformed hands, fused fingers, extra fingers, cropped feet, cropped head, "
    "inconsistent proportions, unreadable face, text, logo, watermark, signature, "
    "speech bubble, caption, comic panel, border, multiple views, character turnaround sheet"
)

DEFAULT_POSITIVE = (
    "masterpiece, best quality, score_7, score_8, @horn/wood,\n"
    "1girl, yukino \\(blue archive\\), serafuku,\n"
    "standing, cowboy shot, looking at viewer, straight-on, white background,"
)

# A lora slot is (name, strength). "None" disables the slot.
LoraSlot = Tuple[str, float]


@dataclass
class GlobalSettings:
    # Model / text-encoder / vae
    model_name: str = "Anima_-_base-v1-0.safetensors"
    weight_dtype: str = "default"
    clip_name: str = "qwen_3_06b_base.safetensors"
    clip_type: str = "stable_diffusion"
    vae_name: str = "qwen_image_vae.safetensors"
    model_shift: float = 3.0

    # LoRA stack (rgthree) — manually typed name + strength
    loras: List[LoraSlot] = field(
        default_factory=lambda: [
            ("None", 0.8),
            ("None", 0.8),
            ("None", 0.8),
            ("None", 0.8),
        ]
    )

    # Resolution / batching
    width: int = 768
    height: int = 1152
    count_per_item: int = 1

    # Seed
    seed: int = 1107471862347394
    seed_mode: str = "fixed"  # fixed | randomize | increment

    # Sampling
    steps: int = 50
    refiner_step: int = 12
    cfg: float = 4.5
    sampler_name: str = "euler"
    scheduler: str = "simple"
    denoise: float = 1.0

    # Prompts
    negative_prompt: str = DEFAULT_NEGATIVE
    positive_prompt: str = DEFAULT_POSITIVE
    pose_strength: str = "1.35"

    # Output / files
    character_folder: str = "AnimaActions/Yukino"
    remove_background: bool = True
    birefnet_model: str = "BiRefNet_toonout"
    upscale_method: str = "lanczos"
    upscale_factor: float = 1.5

    # Connection / where to store results locally
    comfy_url: str = "http://127.0.0.1:8188"
    output_base: str = "./output"

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "weight_dtype": self.weight_dtype,
            "clip_name": self.clip_name,
            "clip_type": self.clip_type,
            "vae_name": self.vae_name,
            "model_shift": self.model_shift,
            "loras": [[n, s] for n, s in self.loras],
            "width": self.width,
            "height": self.height,
            "count_per_item": self.count_per_item,
            "seed": self.seed,
            "seed_mode": self.seed_mode,
            "steps": self.steps,
            "refiner_step": self.refiner_step,
            "cfg": self.cfg,
            "sampler_name": self.sampler_name,
            "scheduler": self.scheduler,
            "denoise": self.denoise,
            "negative_prompt": self.negative_prompt,
            "positive_prompt": self.positive_prompt,
            "pose_strength": self.pose_strength,
            "character_folder": self.character_folder,
            "remove_background": self.remove_background,
            "birefnet_model": self.birefnet_model,
            "upscale_method": self.upscale_method,
            "upscale_factor": self.upscale_factor,
            "comfy_url": self.comfy_url,
            "output_base": self.output_base,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GlobalSettings":
        loras = [tuple(x) for x in d.get("loras", [])]
        # Always normalise to exactly 4 slots
        while len(loras) < 4:
            loras.append(("None", 0.8))
        loras = loras[:4]
        return cls(
            model_name=d.get("model_name", cls.model_name),
            weight_dtype=d.get("weight_dtype", cls.weight_dtype),
            clip_name=d.get("clip_name", cls.clip_name),
            clip_type=d.get("clip_type", cls.clip_type),
            vae_name=d.get("vae_name", cls.vae_name),
            model_shift=float(d.get("model_shift", cls.model_shift)),
            loras=loras,
            width=int(d.get("width", cls.width)),
            height=int(d.get("height", cls.height)),
            count_per_item=int(d.get("count_per_item", cls.count_per_item)),
            seed=int(d.get("seed", cls.seed)),
            seed_mode=d.get("seed_mode", cls.seed_mode),
            steps=int(d.get("steps", cls.steps)),
            refiner_step=int(d.get("refiner_step", cls.refiner_step)),
            cfg=float(d.get("cfg", cls.cfg)),
            sampler_name=d.get("sampler_name", cls.sampler_name),
            scheduler=d.get("scheduler", cls.scheduler),
            denoise=float(d.get("denoise", cls.denoise)),
            negative_prompt=d.get("negative_prompt", cls.negative_prompt),
            positive_prompt=d.get("positive_prompt", cls.positive_prompt),
            pose_strength=str(d.get("pose_strength", cls.pose_strength)),
            character_folder=d.get("character_folder", cls.character_folder),
            remove_background=bool(d.get("remove_background", cls.remove_background)),
            birefnet_model=d.get("birefnet_model", cls.birefnet_model),
            upscale_method=d.get("upscale_method", cls.upscale_method),
            upscale_factor=float(d.get("upscale_factor", cls.upscale_factor)),
            comfy_url=d.get("comfy_url", cls.comfy_url),
            output_base=d.get("output_base", cls.output_base),
        )


@dataclass
class Expression:
    label: str = ""
    prompt: str = ""

    def to_dict(self) -> dict:
        return {"label": self.label, "prompt": self.prompt}

    @classmethod
    def from_dict(cls, d: dict) -> "Expression":
        return cls(label=d.get("label", ""), prompt=d.get("prompt", ""))


@dataclass
class Preset:
    name: str = "Untitled"
    globals: GlobalSettings = field(default_factory=GlobalSettings)
    expressions: List[Expression] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "name": self.name,
            "globals": self.globals.to_dict(),
            "expressions": [e.to_dict() for e in self.expressions],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Preset":
        return cls(
            name=d.get("name", "Untitled"),
            globals=GlobalSettings.from_dict(d.get("globals", {})),
            expressions=[Expression.from_dict(e) for e in d.get("expressions", [])],
        )

    @classmethod
    def default(cls) -> "Preset":
        return cls(name="Untitled", globals=GlobalSettings(), expressions=[])
