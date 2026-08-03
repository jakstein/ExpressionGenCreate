"""Builds a ComfyUI API-format workflow graph from a Preset.

The graph mirrors the Anima_Full_Body reference workflow:

  * One shared model/VAE/CLIP/LoRA pipeline, one shared negative prompt, one
    shared latent (EmptyLatentImage -> 2x RepeatLatentBatch), one rgthree
    Seed node and one rgthree KSampler Config node driving every branch.
  * One branch per Expression: a positive CLIPTextEncode whose text is
    ``<positive_prompt>, (<modifier>:<pose_strength>)`` -> KSampler ->
    VAEDecode -> ImageScaleBy(1.5x) -> (optional BiRefNetRMBG) ->
    SaveImage(<character_folder>/<label>) + PreviewImage.

Only standard ComfyUI nodes plus BiRefNetRMBG are used. Every node's
class_type and input names were verified against the actual node definitions.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .models import Preset, GlobalSettings, Expression


class _Builder:
    """Minimal API-graph builder with an auto-incrementing integer node id."""

    def __init__(self) -> None:
        self.nodes: Dict[str, dict] = {}
        self._nid = 0

    def add(self, class_type: str, **inputs) -> str:
        self._nid += 1
        nid = str(self._nid)
        # Drop None inputs so ComfyUI falls back to node defaults.
        clean = {k: v for k, v in inputs.items() if v is not None}
        self.nodes[nid] = {"class_type": class_type, "inputs": clean}
        return nid


def build_api_graph(preset: Preset):
    """Return ``(api_graph_dict, save_node_map)``.

    ``save_node_map`` maps each SaveImage node id -> expression label so the
    caller can match returned images to expressions.
    """
    g: GlobalSettings = preset.globals
    b = _Builder()

    # ---- Shared model pipeline -------------------------------------------
    unet = b.add("UNETLoader", unet_name=g.model_name, weight_dtype=g.weight_dtype)
    model_patched = b.add("ModelSamplingAuraFlow", model=[unet, 0], shift=g.model_shift)
    clip = b.add("CLIPLoader", clip_name=g.clip_name, type=g.clip_type)
    vae = b.add("VAELoader", vae_name=g.vae_name)

    # Chain standard LoraLoader nodes (rgthree's "Lora Loader Stack" is
    # deprecated and mis-validates the model link on some ComfyUI builds).
    # Note: CLIPLoader exposes CLIP at output index 0, but LoraLoader exposes
    # CLIP at index 1, so track the correct clip output index through the chain.
    cur_model, cur_clip, cur_clip_idx = model_patched, clip, 0
    for name, strength in g.loras:
        if not name or name == "None" or strength == 0:
            continue
        lora_node = b.add(
            "LoraLoader",
            model=[cur_model, 0],
            clip=[cur_clip, cur_clip_idx],
            lora_name=name,
            strength_model=float(strength),
            strength_clip=float(strength),
        )
        cur_model = lora_node
        cur_clip = lora_node
        cur_clip_idx = 1
    final_model: Tuple[str, int] = (cur_model, 0)
    final_clip: Tuple[str, int] = (cur_clip, cur_clip_idx)

    # ---- Shared sampling config ------------------------------------------
    kc = b.add(
        "KSampler Config (rgthree)",
        steps_total=g.steps,
        refiner_step=g.refiner_step,
        cfg=g.cfg,
        sampler_name=g.sampler_name,
        scheduler=g.scheduler,
    )

    # ---- Shared latent ----------------------------------------------------
    empty = b.add(
        "EmptyLatentImage",
        width=g.width,
        height=g.height,
        batch_size=g.count_per_item,
    )
    latent = empty

    # ---- Shared negative prompt ------------------------------------------
    neg = b.add("CLIPTextEncode", clip=final_clip, text=g.negative_prompt)

    # ---- Seed nodes -------------------------------------------------------
    if g.seed_mode in ("fixed", "randomize"):
        shared_seed = b.add(
            "Seed (rgthree)", seed=(g.seed if g.seed_mode == "fixed" else -1)
        )

    # ---- Per-expression branches -----------------------------------------
    save_map: Dict[str, str] = {}
    for idx, expr in enumerate(preset.expressions):
        if g.seed_mode == "increment":
            seed_node = b.add("Seed (rgthree)", seed=g.seed + idx)
        else:
            seed_node = shared_seed

        pos_text = f"{g.positive_prompt}, ({expr.prompt}:{g.pose_strength})"
        pos = b.add("CLIPTextEncode", clip=final_clip, text=pos_text)

        ks = b.add(
            "KSampler",
            model=final_model,
            positive=[pos, 0],
            negative=[neg, 0],
            latent_image=[latent, 0],
            seed=[seed_node, 0],
            steps=[kc, 0],
            cfg=[kc, 2],
            sampler_name=[kc, 3],
            scheduler=[kc, 4],
            denoise=g.denoise,
        )
        vae_decode = b.add("VAEDecode", samples=[ks, 0], vae=[vae, 0])
        scale = b.add(
            "ImageScaleBy",
            image=[vae_decode, 0],
            upscale_method=g.upscale_method,
            scale_by=g.upscale_factor,
        )

        if g.remove_background:
            biref = b.add(
                "BiRefNetRMBG",
                image=[scale, 0],
                model=g.birefnet_model,
                mask_blur=0,
                mask_offset=0,
                invert_output=False,
                refine_foreground=False,
                background="Alpha",
                background_color="#222222",
            )
            img_out: Tuple[str, int] = (biref, 0)
        else:
            img_out = (scale, 0)

        prefix = f"{g.character_folder}/{expr.label}"
        save = b.add("SaveImage", images=img_out, filename_prefix=prefix)
        b.add("PreviewImage", images=img_out)
        save_map[save] = expr.label

    return b.nodes, save_map
