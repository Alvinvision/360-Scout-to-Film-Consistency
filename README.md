# One location, many viewpoints

**360 Scout to Film Consistency** helps filmmakers and creators develop connected AI shots from a single 360° panorama, without building and managing a complex 3D scene.

Start with a **2:1 equirectangular (lat-long) panorama**: capture it with a 360 camera, stitch it from traditional photographs, or create it digitally. Inside ComfyUI, the tool turns that image into overlapping perspective references, giving different POVs and generations a shared visual foundation for the location’s layout, architecture, props, and styling.

Adjust the viewing direction and field of view, then use the references with **Seedance 2.5 or MiniMax H3** to explore your scene. Try it with your own location or designed set, and share your experiments, feedback, and ideas for what comes next.

Built by Alvin Cruz for the Open Source Higgsfield challenge, October 2026.

## Use your own location, references and prompt

Start with your own **2:1 lat-long 360 panorama**. It can be photographed, stitched or digitally created. Upload it in the panorama input, then choose the front direction, field of view and other extraction settings. The default pack creates **five overlapping location views**. You can adjust the views and output size to suit your project.

The extractor handles **only the location image and lens settings**. It does not choose the cast or direct the video. Its outputs are location tiles, a contact sheet, a location/lens reference prompt and a manifest.

Add your own **character references or talent references** in the separate image-input nodes at the video stage. These inputs connect directly to the video model, alongside the location tiles. The people and location shown in the demo are examples; you can replace them with your own references after downloading and installing the tool.

Edit the **video prompt** on the video node before generating. Change the action, scene, camera movement and shot directions to match what you want to make. The included four-shot prompt is a starting point. Keep its image numbers aligned with the references you connect, and use durations and input counts supported by the selected model.

You can also make an environment-only video. Disconnect character references from the video model, remove or mute unused character image-input nodes, and remove character directions from the video prompt. Local panorama extraction does not require character references or video generation.



## Demo

64-second captioned walkthrough: the extractor interface, overlapping reference export, ComfyUI workflow wiring, and completed Seedance 2.5 and MiniMax H3 clips.

https://github.com/user-attachments/assets/2b4903ff-5f03-4450-870f-c5276b74c5e2

[Open the video](https://github.com/user-attachments/assets/2b4903ff-5f03-4450-870f-c5276b74c5e2) · [Download the MP4](https://github.com/Alvinvision/360-Scout-to-Film-Consistency/raw/refs/heads/main/assets/demo.mp4)

The walkthrough and screenshots show the earlier interface. Version 0.2 removes casting and shot controls from the extractor; those now live downstream in the video workflow.

![Earlier extractor interface](assets/extractor.jpg)

## What works

- Five custom nodes and an interactive browser panel inside ComfyUI.
- A location-only **360 Location** extractor: front direction, horizontal FOV, pitch, roll, view count and output size.
- Rectilinear and General Panini (Natural Wide) projections using the same planner for previews and exports.
- Batch processing, paired captures, overlap review, clean PNGs, contact sheets, prompts, manifests and ZIP downloads.
- Separate Seedance 2.5 and MiniMax H3 graphs: five location tiles plus two independent talent image-reference inputs at the video stage.
- Completed ten-second model demonstrations; generated spatial consistency varies by run.

## Install in an existing ComfyUI

Use a recent ComfyUI installation that includes the Seedance 2.5 and MiniMax H3 partner nodes. Tested with ComfyUI 0.43.0, frontend 1.57.4, Python 3.12.16 on Apple Silicon macOS. The extractor uses CPU projection and does not require a local video model or GPU. Other platforms have not been tested.

1. Download or clone this repository.
2. Copy `custom_nodes/comfyui_osmo360` into your `ComfyUI/custom_nodes/` directory.
3. Install its requirements with the Python interpreter used by ComfyUI:

```sh
python -m pip install -r custom_nodes/comfyui_osmo360/requirements.txt
```

4. Restart ComfyUI, then refresh its browser page.
5. Generate the included synthetic example, replacing `/path/to/ComfyUI` with your actual installation:

```sh
python scripts/make_demo_panorama.py /path/to/ComfyUI/input/osmo360/demo_panorama.png
```

6. Drag `workflows/Osmo360_Extraction_Review.json` onto ComfyUI. Run it to extract five views and a contact sheet. Open **360 Reference Extractor** on its extractor node to change camera settings, import your own 2:1 panorama and export a ZIP. This extraction-only graph makes no paid API call.

## Generate video

Import either `Osmo360_Seedance25_Studio.json` or `Osmo360_MiniMaxH3_Studio.json`. Select or upload your panorama in the original panorama node. Use the independent **TALENT 1** and **TALENT 2** image-reference nodes to upload identity references. The extractor processes only the location panorama; edit casting, blocking and shot directions on the video node. Keep five location views first, followed by talent A and talent B. Do not run the video graph with missing talent inputs.

Click **Refresh image previews** to check the local reference path. Authenticate with ComfyUI and use a funded workspace before pressing **Run** for the full graph. Partner model generation requires internet access and consumes Comfy credits. Image references and prompts are sent to the selected provider. Model availability and pricing are controlled by Comfy and its providers.

The video nodes use Comfy's current dynamic input schema. The included frontend restores the serialized reference connections after loading. If a graph reports a missing partner node, update ComfyUI and verify partner-node availability for your account. Use the standard Save Video node to play or download the result.

![Working graph and completed output](assets/workflow.jpg)

## Upgrade existing workflows

Version 0.2 automatically separates talent and video prompts when older UI workflows load. Location extraction has four outputs: references, contact sheet, location/lens prompt and manifest. Talent images connect to the video model through independent image-reference nodes. Re-save the migrated graph. Internal node identifiers and the `comfyui_osmo360` installation directory stay stable for compatibility.

## Verify

From the repository root, with dependencies and ComfyUI's torch/aiohttp available:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s custom_nodes/comfyui_osmo360/tests -v
```

Fourteen backend checks passed on the development Mac. Tests cover projection, seams, profiles, tensor selection, complete exports, source preservation, confined paths, concurrent previews, cancellation and a location-only extractor contract. Real-image comparisons against the native V3 renderer had mean RGB errors below 0.36/255 across seven cases.

## Limits and licenses

This is a local/self-hosted custom pack. It has not been deployed to official Comfy Cloud; importing a workflow does not install a custom node pack there. Panoramas supply image references, not measured 3D geometry. Camera translation, performer identity, exact shot timing and unseen surfaces remain generative. HDR metadata is not automatically detected; exports are SDR RGB and pairing does not fuse HDR.

Original code is MIT licensed; adapted Comfy workflow templates retain their MIT notice in `TEMPLATE_LICENSE`. Third-party models and services retain their own licenses and terms. Example screenshots and the demonstration video are review media and are excluded from the software MIT grant. Private source panoramas and performer source images are not distributed. Use your own permitted inputs or the included synthetic panorama.
