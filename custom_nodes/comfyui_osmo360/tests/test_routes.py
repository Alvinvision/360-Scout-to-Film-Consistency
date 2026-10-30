import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from comfyui_osmo360.routes import Service


class Request:
    def __init__(self, data=None, **match):
        self.data = data or {}
        self.match_info = match
    async def json(self):
        return self.data


class PreviewRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.input = self.root / "input"
        self.input.mkdir()
        Image.new("RGB", (512, 256), "#6393ac").save(self.input / "source.png")
        self.service = Service(self.input, self.root / "output")
        self.settings = {"panorama": "source.png", "width": 128, "height": 72, "location": "RouteTest"}

    def tearDown(self):
        self.temporary.cleanup()

    async def test_concurrent_previews_and_panini(self):
        responses = await asyncio.gather(*[
            self.service.preview(Request(dict(self.settings, fov=100 + i,
                                             projection="Natural Wide" if i == 2 else "Rectilinear")))
            for i in range(3)])
        for response in responses:
            data = json.loads(response.text)
            self.assertEqual(len(data["previews"]), 5)
            self.assertTrue(data["previews"][0]["image"].startswith("data:image/jpeg;base64,"))
            self.assertNotIn("dialogue_prompt", data)
            self.assertIn("Horizontal FOV", data["prompt"])
            self.assertNotIn("Brais", data["prompt"])
            self.assertNotIn("Noa", data["prompt"])

    async def test_export_job_receipt_and_download(self):
        response = await self.service.export(Request(self.settings))
        job_id = json.loads(response.text)["id"]
        state = self.service.jobs[job_id]
        await state["task"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["completed_views"], state["total_views"])
        folder = state["packs"][0]["name"]
        archive = next((self.service.output_root / folder).glob("*.zip"))
        download = await self.service.download(Request(folder=folder, name=archive.name))
        self.assertEqual(download.status, 200)

    async def test_cancelled_export_is_not_marked_complete(self):
        response = await self.service.export(Request(self.settings))
        job_id = json.loads(response.text)["id"]
        await self.service.cancel(Request(job=job_id))
        await self.service.jobs[job_id]["task"]
        self.assertEqual(self.service.jobs[job_id]["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
