# Upgrading to the 360 Location namespace

This release uses `comfyui_location360` for the package, `Location360` for extractor node IDs, `/location360/` for local routes, and `location360/` for new reference exports. The Python imports, browser extension, saved connection properties and workflow files use the same namespace.

## Replace the installed package

1. Save a backup of your existing workflows, prompts and extractor settings.
2. Stop ComfyUI.
3. Move the previous 360-reference custom-node folder **outside** `ComfyUI/custom_nodes/`. Keep the backup outside that directory so ComfyUI does not load two copies of the tool.
4. Copy this repository's `custom_nodes/comfyui_location360` into `ComfyUI/custom_nodes/`.
5. Install its requirements using ComfyUI's Python, restart ComfyUI, and refresh the browser page.
6. Import the new workflow JSON files from `workflows/`. Select your panorama and character references again, then transfer your own prompt and settings from the backup.
7. Run a local input preview before requesting video generation.

Renaming only the installed folder is insufficient: the node identifiers, route names and saved connection properties changed too. Previous internal node IDs are not registered as aliases. An older graph can therefore show missing nodes until it is rebuilt with the new nodes. The supplied graphs already contain the updated IDs and connections.

Your existing image and video files do not need to be deleted or reprocessed. Reselect their actual input paths in the new graph. Previously exported packs stay where they were; new packs use the new output folder. Saved video previews remain dependent on the output files in the ComfyUI instance that produced them.

## Check the upgrade

- The custom-node folder is named `comfyui_location360`.
- **360 Location Extractor** opens its panel and returns five previews.
- Both character files load in the comparison graph.
- Image slots 1–5 are location views; slots 6 and 7 are the character references.
- Both video prompt inputs connect to the shared prompt node.
- The local preview buttons exclude video generation.

If the panel or run controls are missing, inspect the ComfyUI startup log for package import errors and refresh the browser. If a video model is missing, update ComfyUI and verify its availability to your Comfy account. Do not reinstall a second copy of the old package alongside the new one.
