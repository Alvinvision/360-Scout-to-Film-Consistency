# Setup

Use an existing local or self-hosted ComfyUI installation. The extractor runs on the CPU; video generation uses Comfy partner services and a funded Comfy workspace. Importing a graph into Comfy Cloud does not install this custom package.

## Install the package

1. Download or clone this repository.
2. Copy `custom_nodes/comfyui_location360` into your installation's `custom_nodes` directory.
3. Using the Python interpreter that runs ComfyUI, install the requirements:

   ```sh
   python -m pip install -r custom_nodes/comfyui_location360/requirements.txt
   ```

4. Restart ComfyUI and refresh its browser page. For an existing installation of this tool, follow [Upgrading](UPGRADING.md) first.
5. Drag a JSON file from `workflows/` onto the canvas. Begin with `360Location_Extraction_Review.json` for a local-only test, or `360Location_Seedance25_MiniMaxH3_Compare.json` for the shared video workflow.

## Supply the images

Upload your own 2:1 equirectangular panorama, or use the [example panorama](https://github.com/Alvinvision/360-Scout-to-Film-Consistency/raw/refs/heads/main/assets/CAM_20260924124608_0036_D.JPG). A source can be captured with a 360 camera, stitched from photographs or created digitally.

In **Open 360 Reference Extractor**, start with:

| Control | Value |
| --- | --- |
| Reference pack | Seedance Landscape |
| Horizontal FOV | 115° |
| Projection | Natural Wide |
| Edge-stretch reduction | 100 |
| Pitch | 0° |
| Views | 5, spaced 72° apart |
| Output per view | 2048 × 1152 |
| Show overlap | On, for preview inspection |

Choose the front direction and adjust the settings to suit your location. Resetting a preset can change the saved values. Overlap guides do not appear in exported PNGs.

For video, select your own images in both character-reference nodes. The graphs contain placeholder filenames; character images and rendered clips are not bundled into the workflow JSON. The model receives five location views followed by Character A and Character B. Change those character directions in the prompt to match your references.

## Preview and generate

- **Refresh image previews** on the extractor checks the panorama and reference tiles locally.
- **Preview inputs · local** in the comparison workflow also checks both character images.
- **Run Seedance · credits**, **Run MiniMax · credits**, or **Run both · credits** starts the selected video branch after Comfy sign-in. Confirm the intended funded workspace before running.

The comparison workflow defaults to a four-shot, fifteen-second example with one shared prompt and fixed seeds. The separate video workflows are ten-second examples with prompts on their individual model nodes. Adapt the action, references, camera moves, duration and seed behavior before generating.

The standard **Run** button on the comparison graph includes both video models. Each model has a separate Save Video player. Save the workflow after completion to retain its preview references; the underlying output files must remain on that ComfyUI instance.

Seedance's example has audio generation disabled. The MiniMax node tested here does not expose an audio/music switch; if a video-only delivery is required, remove any audio track during export. The local validation deliveries were exported this way.

## Files and outputs

The package registers `Location360PanoramaInput`, `Location360ReferencePack`, `Location360SelectView`, `Location360DialoguePrompt`, and `LocationReferenceImage`. The browser panel uses local `/location360/` endpoints. Reference packs are written beneath `output/location360/`; the supplied video nodes use `location360/video/` output prefixes.

The optional synthetic source can be generated without downloading an image:

```sh
python scripts/make_demo_panorama.py /path/to/ComfyUI/input/location360/demo_panorama.png
```

See the [main README](../README.md) for advanced extraction options, limits and licenses.
