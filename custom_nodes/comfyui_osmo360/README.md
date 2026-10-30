# 360 Location Extractor for ComfyUI

Turn any stitched **2:1 equirectangular (lat-long) panorama** into overlapping perspective references. The source can come from any 360 camera, a stitched photographic panorama, or a digitally created environment.

The extractor processes the location image only: panorama/folder import, source queue, front direction, FOV, pitch, roll, projection, Natural Wide strength, overlap review, source profiles, paired captures, output sizing and batch export. Preview and export share the same camera planner. Originals remain unchanged.

## Install

Copy `comfyui_osmo360` into `ComfyUI/custom_nodes/`, install `requirements.txt` with ComfyUI's Python, and restart ComfyUI and refresh the browser. Open **360 Location → Images → 360 Location Extractor**, then **Open 360 Reference Extractor**. Torch and aiohttp come from ComfyUI. HEIC requires pillow-heif and supported platform dependencies. This is a local/self-hosted custom pack; importing a workflow into official Comfy Cloud does not install it there.

## Location outputs

`Osmo360ReferencePack` returns exactly four outputs:

- `references`: a batch of clean perspective images.
- `contact_sheet`: a visual overview of the location views.
- `reference_prompt`: viewing directions, lens/FOV information, and relationships between the location references.
- `manifest`: camera geometry, source metadata and view filenames as JSON.

`Osmo360PanoramaInput` previews the original panorama and supports upload/file selection. `Osmo360SelectView` selects a zero-based tile and displays it inline. Batch processing maps outputs per panorama.

Talent, casting, actor blocking and shot timing belong to the **video stage**. The Seedance 2.5 and MiniMax H3 examples use independent **Image Reference / Upload** nodes for talent A and B, connected directly to model reference slots after the five location tiles. Edit the shot prompt on the video node. The extractor neither reads talent files nor generates a talent/shot prompt. Its **Refresh image previews** button runs only local location processing.

## Upgrade from 0.1

Version 0.2 migrates older saved UI workflows when they load: old extractor talent outputs become independent image-reference nodes, and old shot-prompt links move to editable video-node text. Existing inline prompts, identity file selections and saved render previews are retained. Re-save the migrated graph. Internal node IDs, package directory and API routes keep their original names for workflow compatibility; displayed branding is **360 Location**. The optional legacy dialogue helper is a separate video-prompt node. The independent image input accepts existing files in Comfy input subfolders as well as new uploads.

## Export and verification

Exports go beneath Comfy's output `osmo360/` directory. ZIPs contain clean PNGs, contact sheet, location/lens prompt, manifest and optional exact source copies. Uploads stay inside Comfy input. Incomplete exports are marked `INCOMPLETE.txt`. No API key is stored in the extension.

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s custom_nodes/comfyui_osmo360/tests -v
node custom_nodes/comfyui_osmo360/tests/test_workflow_migration.mjs
```

Fourteen Python checks cover projection, seams, profiles, tensor selection, complete exports, source preservation, confined paths, concurrent previews, cancellation, and the location-only extraction contract. JavaScript migration checks cover independent talent wiring, prompt separation, retained lens values, preview preservation and repeat loads. Seven earlier comparisons against native V3 had mean RGB differences below 0.36/255.

## Limits

Tested on Apple Silicon macOS with ComfyUI 0.43.0, frontend 1.57.4 and Python 3.12.16. Other platforms have not been tested. A single panorama is not measured 3D geometry: video camera translations and hidden surfaces remain generative. HDR metadata is not automatically detected; exports are SDR RGB and paired captures do not fuse HDR. Paired captures must share the same physical position. Preview enlargement uses a bounded image rather than decoding the full source in the browser. Partner video generation requires Comfy sign-in, internet access and credits.
