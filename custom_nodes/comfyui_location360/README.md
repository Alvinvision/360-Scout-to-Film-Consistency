# 360 Location Extractor for ComfyUI

Turn a stitched **2:1 equirectangular (lat-long) panorama** into overlapping perspective references inside ComfyUI. The source can come from a 360 camera, stitched traditional photographs or a digitally created environment. With the recommended settings, extracted references are **2048 × 1152 (16:9)**.

**Please read the [main README](../../README.md) before running a workflow.** It contains installation steps, the recommended **115° FOV / Natural Wide / edge-stretch reduction 100** settings, and instructions for the local preview and paid video controls. The workflow files may open with different extractor values; apply the recommendations yourself.

[Download the example 2:1 panorama](https://github.com/Alvinvision/360-Scout-to-Film-Consistency/raw/refs/heads/main/assets/CAM_20260924124608_0036_D.JPG) to try the same location as the demo. Upload the JPEG in the panorama input or through **Add panoramas**, then apply the recommended settings. Character images are not supplied. The panorama is provided for trying and evaluating this project; see the repository’s [media notice](../../MEDIA_NOTICE.txt).

## Install and open

Copy `comfyui_location360` into `ComfyUI/custom_nodes/`, install its `requirements.txt` with ComfyUI’s Python, restart ComfyUI and refresh the browser. PyTorch and aiohttp are supplied by ComfyUI. HEIC support depends on pillow-heif and its platform decoder.

Import a workflow from the repository’s `workflows/` folder. On **360 Location Extractor**, click **Open 360 Reference Extractor** to add a panorama, choose the front direction, adjust lens settings and inspect overlapping previews. The panel can also export reference packs. The original source stays unchanged.

## Location outputs

`Location360ReferencePack` has four outputs:

| Output | Contents |
| --- | --- |
| `references` | Clean perspective images, grouped per panorama. |
| `contact_sheet` | An overview of the extracted views. |
| `reference_prompt` | Location viewing directions and lens information as text. |
| `manifest` | Camera settings, source metadata and view filenames as JSON. |

`Location360PanoramaInput` selects and previews the source panorama. `Location360SelectView` selects a reference by its zero-based index. `LocationReferenceImage` loads a separate image for the video stage. The optional `Location360DialoguePrompt` is a legacy video-prompt helper, not part of the supplied combined workflow.

The extractor does not choose the cast or direct the video. In the supplied video graphs, five location views connect directly to the video model, followed by two independent character images. A ZIP download is not needed to pass those images downstream. The extractor’s location prompt is available to copy; the video graphs do not automatically include it in their generation prompt.

## Preview and generate

**Refresh image previews** on the extractor runs the local location nodes. In the combined workflow, **Preview inputs · local** on **SHARED VIDEO PROMPT** also previews both character inputs, so those files must be selected first. Neither action requests video generation.

For the combined workflow, edit **SHARED VIDEO PROMPT** and use **Run Seedance · credits**, **Run MiniMax · credits** or **Run both · credits**. Standard ComfyUI **Run** executes both branches. In the separate model workflows, edit the prompt on the video node and use standard **Run** for that one model. Video generation requires Comfy sign-in, internet access and workspace credits; connected references and prompts are sent to the provider.

## Exports and advanced options

Packs are saved under ComfyUI’s `output/location360/` directory. They contain clean PNGs, a contact sheet, a location/lens prompt, a manifest and optional source copies. Use **Export references** in the panel to create a pack and show its download link. Executing the extractor node also writes a pack to disk. Incomplete exports are marked `INCOMPLETE.txt`.

Batch export, paired captures, custom view counts and output sizing are available in the extractor. Paired captures must share the same physical camera position; batch mode must be off when using a pair. The supplied video workflows select five location views, so use the extraction-only graph when exploring other pack layouts.

## Update and verify

Version 0.3 uses package `comfyui_location360`, `Location360` node IDs and `/location360/` routes. Move the previous 360-reference package outside the custom-node directory, install this pack as the only copy, restart ComfyUI and refresh the browser. Use the new workflow files and reselect your inputs; previous internal IDs are not kept as aliases. See the [upgrade guide](../../docs/UPGRADING.md).

Run these commands from the repository root, using a Python environment with the dependencies, PyTorch and aiohttp, plus Node.js for the JavaScript checks:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s custom_nodes/comfyui_location360/tests -v
node custom_nodes/comfyui_location360/tests/test_comparison_workflow.mjs workflows/360Location_Seedance25_MiniMaxH3_Compare.json
node custom_nodes/comfyui_location360/tests/test_workflow_migration.mjs
```

All 14 backend tests and the comparison and migration checks pass. The renamed local setup also completed Seedance 2.5 and MiniMax H3 generations and reloaded both saved video players on 2 November 2026. See [verification notes](../../docs/VERIFICATION.md).

## Limits

Tested on Apple Silicon macOS with ComfyUI 0.43.0, frontend 1.57.4 and Python 3.12.16. The extractor uses CPU projection. Other platforms have not been tested. This is a local/self-hosted custom pack; importing JSON into Comfy Cloud does not install it there.

A panorama supplies visual references, not measured 3D geometry. Video layout, identity, translated camera views, hidden surfaces and shot timing can vary. HDR metadata is not automatically detected, exports are SDR RGB and paired captures do not fuse HDR. See the [main README](../../README.md#limits-and-licenses) for licenses and media terms.
