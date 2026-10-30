# Osmo 360 Reference Extractor for ComfyUI

Custom Python nodes and a browser frontend for turning a stitched 2:1 panorama into overlapping location references. Open **Osmo360 → Location → Osmo360ReferencePack**, then click **Open 360 Reference Extractor**.

The panel provides panorama/folder import, a source queue, per-source front rotation, live reference previews, presets, FOV, pitch, roll, Natural Wide strength, overlap display, source profiles, paired captures, output sizing, talent references, a generated four-shot prompt, batch export, progress, cancellation and ZIP downloads. Preview and export share the same camera planner and renderer. Originals are read without modification.

## Installation

This requires a ComfyUI server on which custom nodes can be installed. Copy this entire `comfyui_osmo360` directory into the server's `ComfyUI/custom_nodes/`, install `requirements.txt` using that server's Python environment, and restart ComfyUI. Torch and aiohttp come from ComfyUI. HEIC needs pillow-heif and its supported platform dependencies.

Official Comfy Cloud does not currently let users install arbitrary custom packs. This package has **not been installed in Comfy Cloud**. Its deployment there requires Comfy to accept and expose both its Python nodes and frontend extension. Importing the example JSON cannot install them. See [Cloud policy](https://docs.comfy.org/get_started/cloud).

## Outputs and model wiring

`Osmo360ReferencePack` returns a batch of clean reference images, a review contact sheet, location prompt, manifest JSON, dialogue prompt, and two talent images. `Osmo360SelectView` selects a zero-based image from the batch. Use one selector per model reference slot. Batch source processing maps these outputs per panorama using Comfy's list execution.

The examples keep **five** location views as images 1–5, Brais as image 6, and Noa as image 7. Keep this order when using the generated dialogue prompt. The generic panel adjusts talent indices when the view count changes; model reference limits still apply. A paired pack has twice as many references. Never send a blank talent output to a generation node.

Seedance 2.5 and MiniMax H3 examples use separate references. The hosted LTX 2.5 image-to-video node accepts a first frame and optional last frame, so its talent test requires an inspected scene-and-talent composite first. It is not an equivalent seven-reference interface. Video translations and hidden geometry are inferred by the model; the panorama is not a measured 3D reconstruction.

## Four-shot test

One 10-second generation: 0–3s establishing pan with both performers central; 3–5s three-quarter OTS behind Brais; 5–7s reverse OTS behind Noa; 7–10s an uninterrupted camera arc across their axis, continuing into an environment-revealing pan. Shot 4 has no internal cut. Both performers retain their marks and wardrobe throughout. Exact timing and spatial consistency require visual evaluation of generated results.

## Validation and limits

Thirteen backend tests cover geometry, seams, profiles, tensor selection, source preservation, complete exports, path confinement, concurrent previews and cancellation. Seven real-image comparisons against the native V3 renderer have mean RGB differences below 0.36/255; their 95th-percentile errors are 1/255. JPEG decoding and color management can account for small raster differences.

The pack is now installed and verified inside local ComfyUI v0.43.0, with frontend 1.57.4 and Python 3.12.16. A real extraction graph successfully produced the five-view reference pack and contact-sheet preview. Live FOV, pitch and projection controls also work in the Comfy frontend. Seedance 2.5 and MiniMax H3 four-shot talent renders have also completed using LA Build Night credits. Automatic Apple ImageIO HDR gain-map detection is not implemented: HDR stays unknown unless explicitly confirmed. Paired captures must share the physical camera position. Exports are SDR RGB PNGs; pairing does not fuse HDR. Preview inspection enlarges a bounded preview rather than decoding the full 120MP image in the browser.

Run backend checks from the studio folder:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s custom_nodes/comfyui_osmo360/tests -v
```

Exports are saved beneath the Comfy output directory's `osmo360/` folder. Upload paths are confined to Comfy input. Cancelled or failed folders carry `INCOMPLETE.txt`. ZIPs include clean PNGs, contact sheet, location prompt, manifest and optionally exact source copies. No API key is stored in the extension.

## Visual studio workflows

Use `Osmo360PanoramaInput` for the original 2:1 image preview and native upload/file selection. Its path output connects directly to the extractor. `Osmo360SelectView` displays native inline previews for the five tiles and both talent references. The extractor's **Refresh image previews** button executes only the local image path. Completed workflows persist their own media previews and use distinct node IDs so switching between models does not display the other model's video. Both final workflows have native Save Video playback and downloads.
