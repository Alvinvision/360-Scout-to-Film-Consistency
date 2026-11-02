# Verification

## Tested environment

The renamed local setup was checked on **2 November 2026** with Apple Silicon macOS, Python 3.12.16, ComfyUI 0.43.0 and frontend 1.57.4. Other platforms have not been tested.

## Checks completed

- All 14 Python geometry, export, input-path and HTTP-service tests passed.
- Frontend migration checks passed, including repeat loading without duplicate connections.
- Comparison checks confirmed the same seven image connections and shared prompt reach both models, each model can be targeted separately, and local preview targets exclude video generation.
- The 15,520 × 7,760 test panorama, five 2048 × 1152 Natural Wide views and two independent character references loaded in the renamed local ComfyUI instance.
- Both Seedance 2.5 and MiniMax H3 completed the full comparison workflow using a funded Comfy workspace.
- The delivered clips were exported as 15-second, 24 fps, video-only files: 1280 × 720 for Seedance and 1344 × 768 for MiniMax.
- Both saved video previews reloaded and played in the workflow. Local video-serving checks passed.

These checks establish that the renamed pipeline executes and restores its previews. They do not establish measured 3D accuracy or guarantee that a model preserves every object, identity or cut. Provider output can contain an extra frame or an audio track; the local delivery exports were trimmed and made video-only separately.

The published JSON uses portable example filenames and omits machine-specific previews and cached render results. Select your own inputs before running it. The local render files, screenshots, account data and credentials are not included in this code update. Existing repository images and videos are retained unchanged.

## Run the source checks

From the repository root, using ComfyUI's Python and an installed Node.js runtime:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s custom_nodes/comfyui_location360/tests -v
node custom_nodes/comfyui_location360/tests/test_workflow_migration.mjs
node custom_nodes/comfyui_location360/tests/test_comparison_workflow.mjs workflows/360Location_Seedance25_MiniMaxH3_Compare.json
node scripts/check_workflows.mjs
```

These commands use synthetic test images and inspect workflow wiring; they do not submit paid video generations. For a manual local check, use the extraction-only workflow or the comparison graph's **Preview inputs · local** control.
