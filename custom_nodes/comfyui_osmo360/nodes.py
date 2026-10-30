"""ComfyUI adapters. Image outputs use Comfy's BHWC float tensor convention."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from .core import PRESETS, Settings, dialogue_prompt, export_pack, metadata, read_source


def resolve_input(name):
    import folder_paths
    root = Path(folder_paths.get_input_directory()).resolve()
    candidate = (root / str(name)).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError("Choose an uploaded panorama from the Comfy input directory.")
    return candidate


def tensor(images):
    return torch.from_numpy(np.stack([np.asarray(im.convert("RGB"), dtype=np.float32) / 255 for im in images]))


class Osmo360PanoramaInput:
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        root = Path(folder_paths.get_input_directory())
        files = sorted(str(path.relative_to(root)) for path in root.rglob("*")
                       if path.is_file() and path.suffix.lower() in (".jpg",".jpeg",".png",".tif",".tiff",".heic",".heif"))
        return {"required":{"image":(files,{"image_upload":True})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("panorama_path",)
    FUNCTION = "select"
    CATEGORY = "Osmo360/Location"
    OUTPUT_NODE = True
    DESCRIPTION = "Original lat-long panorama preview. Upload or choose another 2:1 panorama to change the extractor source."

    @classmethod
    def IS_CHANGED(cls,image):
        path = resolve_input(image)
        stat = path.stat()
        return (stat.st_mtime_ns,stat.st_size)

    def select(self,image):
        from PIL import Image
        from nodes import PreviewImage
        path = resolve_input(image)
        metadata(path)
        array,_ = read_source(path,preview=True)
        preview = Image.fromarray(array)
        preview.thumbnail((2048,1024),Image.Resampling.LANCZOS)
        ui = PreviewImage().save_images(tensor([preview]))["ui"]
        return {"ui":ui,"result":(image,)}


class Osmo360ReferencePack:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "panorama": ("STRING", {"default": ""}),
            "preset": (list(PRESETS),),
            "yaw_zero": ("FLOAT", {"default": 0, "min": -360, "max": 360, "step": 1}),
            "fov": ("FLOAT", {"default": 100, "min": 2, "max": 178, "step": 1}),
            "pitch": ("FLOAT", {"default": 0, "min": -90, "max": 90, "step": 1}),
            "roll": ("FLOAT", {"default": 0, "min": -180, "max": 180, "step": 1}),
            "projection": (["Rectilinear", "Natural Wide"],),
            "strength": ("FLOAT", {"default": 100, "min": 0, "max": 100, "step": 1}),
            "width": ("INT", {"default": 2048, "min": 16, "max": 8192}),
            "height": ("INT", {"default": 1152, "min": 16, "max": 8192}),
            "view_count": ("INT", {"default": 5, "min": 1, "max": 24}),
            "spacing": ("FLOAT", {"default": 72, "min": 0.01, "max": 360}),
            "starting_yaw": ("FLOAT", {"default": 0, "min": -360, "max": 360}),
            "upscale": ("BOOLEAN", {"default": False}),
            "profile": (["Auto Detect", "120MP DETAIL", "30MP PANORAMA", "30MP HDR", "360 PANORAMA"],),
            "hdr_capture": ("BOOLEAN", {"default": False}),
            "include_original": ("BOOLEAN", {"default": False}),
            "location": ("STRING", {"default": "Location"}),
            "pair_secondary": ("STRING", {"default": ""}),
            "pair_same_position": ("BOOLEAN", {"default": False}),
            "process_all": ("BOOLEAN", {"default": False}),
            "queue_json": ("STRING", {"default": "[]", "multiline": True}),
            "talent_a": ("STRING", {"default": ""}),
            "talent_b": ("STRING", {"default": ""}),
            "scene_yaw": ("FLOAT", {"default": 216, "min": 0, "max": 360}),
            "wide_fov": ("FLOAT", {"default": 70, "min": 10, "max": 150}),
            "ots_fov": ("FLOAT", {"default": 50, "min": 10, "max": 150}),
            "camera_height": ("FLOAT", {"default": 1.6, "min": 0.3, "max": 3}),
            "cross_fov": ("FLOAT", {"default": 60, "min": 10, "max": 150}),
        }}

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("references", "contact_sheet", "reference_prompt", "manifest",
                    "dialogue_prompt", "talent_a", "talent_b")
    OUTPUT_IS_LIST = (True, True, True, True, True, True, True)
    FUNCTION = "execute"
    CATEGORY = "Osmo360/Location"
    OUTPUT_NODE = True
    DESCRIPTION = "V3 camera controls and reference export. Requires this custom pack to be installed on the Comfy server."

    @classmethod
    def IS_CHANGED(cls, panorama="", pair_secondary="", queue_json="[]", **kwargs):
        import hashlib
        names = [panorama, pair_secondary, kwargs.get("talent_a", ""), kwargs.get("talent_b", "")]
        if kwargs.get("process_all"):
            names += [item.get("path", "") for item in json.loads(queue_json)]
        digest = hashlib.sha256()
        for name in names:
            if name:
                path = resolve_input(name)
                digest.update(str(path).encode())
                stat = path.stat()
                digest.update(str((stat.st_mtime_ns, stat.st_size)).encode())
        return digest.hexdigest()

    def execute(self, panorama, pair_secondary="", pair_same_position=False,
                process_all=False, queue_json="[]", **kwargs):
        import folder_paths
        from comfy.model_management import throw_exception_if_processing_interrupted
        output = Path(folder_paths.get_output_directory()) / "osmo360"
        jobs = json.loads(queue_json) if process_all else [{"path": panorama, "yaw_zero": kwargs.get("yaw_zero", 0)}]
        if not jobs:
            raise ValueError("Import at least one panorama.")
        if len(jobs) > 100:
            raise ValueError("Limit a batch to 100 panoramas.")
        from PIL import Image, ImageOps
        identities = []
        for key in ("talent_a", "talent_b"):
            if kwargs.get(key):
                with Image.open(resolve_input(kwargs[key])) as image:
                    identities.append(tensor([ImageOps.exif_transpose(image).convert("RGB")]))
            else:
                identities.append(torch.zeros((1, 1, 1, 3), dtype=torch.float32))
        refs, sheets, prompts, manifests, packs, dialogues, previews = [], [], [], [], [], [], []
        for entry in jobs:
            throw_exception_if_processing_interrupted()
            config = dict(kwargs)
            config["yaw_zero"] = entry.get("yaw_zero", config.get("yaw_zero", 0))
            paths = [resolve_input(entry["path"])]
            if pair_secondary:
                if process_all:
                    raise ValueError("Pairing applies to the selected source. Disable batch mode for a pair.")
                if not pair_same_position:
                    raise ValueError("Confirm that both captures share exactly the same camera position.")
                paths.append(resolve_input(pair_secondary))
            settings = Settings.from_dict(config)
            images, sheet, prompt, manifest, folder, archive = export_pack(
                output, paths, settings, cancel=throw_exception_if_processing_interrupted)
            refs.append(tensor(images))
            sheets.append(tensor([sheet]))
            prompts.append(prompt)
            dialogues.append(dialogue_prompt(prompt, dict(kwargs, reference_count=len(manifest["views"]))))
            manifests.append(json.dumps(manifest, ensure_ascii=False))
            packs.append({"folder": folder.name, "zip": archive.name,
                          "url": "/osmo360/download/" + folder.name + "/" + archive.name})
            previews.append({"filename":next(folder.glob("*_CONTACTSHEET.jpg")).name,
                             "subfolder":"osmo360/"+folder.name,"type":"output"})
        return {"ui": {"osmo360_packs": packs, "images":previews},
                "result": (refs, sheets, prompts, manifests, dialogues,
                           [identities[0] for _ in refs], [identities[1] for _ in refs])}


class Osmo360SelectView:
    OUTPUT_NODE = True
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"references": ("IMAGE",),
                             "view_index": ("INT", {"default": 0, "min": 0, "max": 47})}}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("reference_image",)
    FUNCTION = "select"
    CATEGORY = "Osmo360/Location"

    def select(self, references, view_index):
        if not 0 <= view_index < references.shape[0]:
            raise ValueError("This view index is outside the current reference pack.")
        selected = references[view_index:view_index + 1]
        try:
            import folder_paths
        except ImportError:
            images = []  # Geometry tests can run without a Comfy host.
        else:
            from nodes import PreviewImage
            images = PreviewImage().save_images(selected)["ui"]["images"]
        return {"ui":{"images":images},"result":(selected,)}


class Osmo360DialoguePrompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "reference_prompt": ("STRING", {"forceInput": True}),
            "reference_count": ("INT", {"default": 5, "min": 1, "max": 48}),
            "scene_yaw": ("FLOAT", {"default": 216, "min": 0, "max": 360}),
            "wide_fov": ("FLOAT", {"default": 70, "min": 10, "max": 150}),
            "ots_fov": ("FLOAT", {"default": 50, "min": 10, "max": 150}),
            "camera_height": ("FLOAT", {"default": 1.6, "min": 0.3, "max": 3}),
            "cross_fov": ("FLOAT", {"default": 60, "min": 10, "max": 150}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("dialogue_prompt",)
    FUNCTION = "build"
    CATEGORY = "Osmo360/Prompts"

    def build(self, reference_prompt, **kwargs):
        return (dialogue_prompt(reference_prompt, kwargs),)
