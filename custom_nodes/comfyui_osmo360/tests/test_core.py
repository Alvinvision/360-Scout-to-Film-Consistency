import io
import json
import math
import sys
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from comfyui_osmo360.core import (
    Settings, camera_plan, classify, dialogue_prompt, effective_settings,
    export_pack, metadata, render, source_coordinates,
)
from comfyui_osmo360.nodes import Osmo360SelectView, tensor
from comfyui_osmo360.routes import Service


class GeometryTests(unittest.TestCase):
    def test_ring_matches_v3_manifest_contract(self):
        settings = Settings()
        cameras, overlaps, uniform = camera_plan(settings)
        self.assertEqual([c["relativeYaw"] for c in cameras], [0, 72, 144, 216, 288])
        self.assertEqual(overlaps, [28] * 5)
        self.assertTrue(uniform)
        self.assertAlmostEqual(cameras[0]["verticalFOV"], 67.67274797076357)
        self.assertAlmostEqual(camera_plan(replace(settings, yaw_zero=37))[0][1]["sourceYaw"], 109)

    def test_center_rays_yaw_and_pitch(self):
        for yaw, expected in [(0, .5), (90, .75), (180, 0), (270, .25)]:
            settings = replace(Settings(), yaw_zero=yaw, pitch=15)
            camera = camera_plan(settings)[0][0]
            u, v = source_coordinates(settings, camera, 2, 2)
            self.assertAlmostEqual(float(u[1, 0]), expected)
            self.assertAlmostEqual(float(v[1, 0]), .5 - 15 / 180)

    def test_asymmetric_orientation_and_seam(self):
        settings = Settings()
        u, v = source_coordinates(settings, camera_plan(settings)[0][0], 9, 5)
        self.assertLess(u[2, 0], u[2, -1])
        self.assertLess(v[0, 4], v[-1, 4])
        settings = replace(settings, yaw_zero=180)
        source = np.full((100, 200, 3), 120, dtype=np.uint8)
        rendered = np.asarray(render(source, settings, camera_plan(settings)[0][0], 64, 32))
        self.assertTrue(np.all(rendered == 120))

    def test_natural_wide_zero_and_vertical_coverage(self):
        rect = Settings(fov=115)
        zero = replace(rect, projection="Natural Wide", strength=0)
        self.assertTrue(all(np.array_equal(a, b) for a, b in zip(
            source_coordinates(rect, camera_plan(rect)[0][0], 19, 11),
            source_coordinates(zero, camera_plan(zero)[0][0], 19, 11))))
        wide = replace(zero, strength=100)
        classic_panini_half_width = 2 * math.tan(math.radians(115 / 4))
        self.assertAlmostEqual(wide.vertical_fov, math.degrees(
            2 * math.atan(classic_panini_half_width * 1152 / 2048)), places=9)
        self.assertLess(wide.vertical_fov, rect.vertical_fov)

    def test_profiles_hdr_and_size_caps(self):
        self.assertEqual(classify(15520, 7760), "120MP DETAIL")
        self.assertEqual(classify(7680, 3840), "30MP PANORAMA")
        with self.assertRaises(ValueError):
            classify(6400, 4800)
        settings = replace(Settings(), width=4096, height=2304)
        detail = {"width": 15520, "height": 7760, "profile": "120MP DETAIL"}
        secondary = {"width": 7680, "height": 3840, "profile": "30MP PANORAMA"}
        self.assertEqual(effective_settings(settings, [detail]).width, 4096)
        pair = effective_settings(settings, [detail, secondary])
        self.assertEqual((pair.width, pair.height), (2048, 1152))
        manually_marked_primary = effective_settings(replace(settings, profile="120MP DETAIL"), [detail, secondary])
        self.assertEqual((manually_marked_primary.width, manually_marked_primary.height), (2048, 1152))

    def test_invalid_geometry(self):
        for settings in [replace(Settings(), fov=float("nan")),
                         replace(Settings(), fov=180), replace(Settings(), strength=101),
                         replace(Settings(), spacing=.01)]:
            with self.assertRaises(ValueError):
                settings.validate()

    def test_tensor_and_selector(self):
        images = [Image.new("RGB", (64, 32), color) for color in ("red", "blue")]
        batch = tensor(images)
        self.assertEqual(tuple(batch.shape), (2, 32, 64, 3))
        selected = Osmo360SelectView().select(batch, 1)["result"][0]
        self.assertEqual(tuple(selected.shape), (1, 32, 64, 3))
        self.assertEqual(float(selected[0, 0, 0, 2]), 1)

    def test_export_preserves_source_and_has_complete_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            Image.new("RGB", (512, 256), "#7389b2").save(source)
            before = source.read_bytes()
            settings = replace(Settings(), width=128, height=72, include_original=True, location="Test")
            _, _, prompt, manifest, folder, archive = export_pack(root / "output", [source], settings)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(len(manifest["views"]), 5)
            for view in manifest["views"]:
                self.assertIn(view["filename"], prompt)
                with Image.open(folder / view["filename"]) as saved:
                    self.assertEqual(saved.size, (128, 72))
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(len([name for name in z.namelist() if name.endswith(".png")]), 6)
            again = export_pack(root / "output", [source], settings)[4]
            self.assertNotEqual(folder, again)

    def test_service_rejects_path_escape_and_unconfirmed_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            service = Service(Path(directory) / "input", Path(directory) / "output")
            with self.assertRaises(ValueError):
                service.source("../outside.png")
            with self.assertRaises(ValueError):
                service.paths({"panorama": "missing.png", "pair_secondary": "other.png"})

    def test_dialogue_identity_axis_and_controls(self):
        text = dialogue_prompt("One location.", {"scene_yaw": 216, "wide_fov": 70, "ots_fov": 50, "camera_height": 1.6})
        for expected in ["Image 6 is Brais", "Image 7 is Noa", "over-Brais-shoulder",
                         "over-Noa-shoulder", "10-second", "EXACTLY FOUR", "70.0-degree", "50.0-degree",
                         "never swap positions", "NO cut or teleportation within shot 4"]:
            self.assertIn(expected, text)
        self.assertIn("concluding pan belongs to shot 4", text)
        self.assertIn("Image 5 is Brais", dialogue_prompt("Location.", {"view_count": 4}))
        self.assertIn("Image 12 is Noa", dialogue_prompt("Paired location.", {"reference_count": 10}))


if __name__ == "__main__":
    unittest.main()
