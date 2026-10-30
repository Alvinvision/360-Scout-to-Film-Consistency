"""Preview/export routes shared by the Comfy extension and its local QA harness."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from aiohttp import web

from .core import Settings, dialogue_prompt, extract, export_pack, metadata, safe_name


class CancelledExport(Exception):
    pass


class Service:
    def __init__(self, input_root, output_root):
        self.input_root = Path(input_root).resolve()
        self.output_root = Path(output_root).resolve() / "osmo360"
        self.jobs = {}
        self.preview_slots = None

    def source(self, name):
        path = (self.input_root / str(name)).resolve()
        if not path.is_relative_to(self.input_root) or not path.is_file():
            raise ValueError("Source must be an uploaded file inside the Comfy input directory.")
        return path

    def paths(self, data):
        paths = [self.source(data["panorama"])]
        if data.get("pair_secondary"):
            if not data.get("pair_same_position"):
                raise ValueError("Confirm the paired captures share exactly the same camera position.")
            paths.append(self.source(data["pair_secondary"]))
        return paths

    async def upload(self, request):
        reader = await request.multipart()
        item = await reader.next()
        if not item or item.name != "file" or not item.filename:
            raise ValueError("Choose a panorama file.")
        folder = self.input_root / "osmo360"
        folder.mkdir(parents=True, exist_ok=True)
        name = uuid.uuid4().hex[:12] + "_" + safe_name(Path(item.filename).name)
        path = folder / name
        size = 0
        try:
            with path.open("wb") as stream:
                while True:
                    chunk = await item.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 500 * 1024 * 1024:
                        raise ValueError("Source file exceeds the 500MB upload limit.")
                    stream.write(chunk)
            if request.query.get("kind") == "talent":
                from PIL import Image
                with Image.open(path) as im:
                    if im.width * im.height > 30_000_000:
                        raise ValueError("Talent reference exceeds 30MP.")
                    meta = {"width": im.width, "height": im.height, "profile": "Talent reference"}
            else:
                meta = await asyncio.to_thread(metadata, path)
            return web.json_response(dict(meta, path=str(path.relative_to(self.input_root)),
                                          display_name=Path(item.filename).name))
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    async def preview(self, request):
        data = await request.json()
        settings = Settings.from_dict(data)
        paths = self.paths(data)
        edge = max(160, min(1280, int(data.get("preview_edge", 640))))
        if self.preview_slots is None:
            self.preview_slots = asyncio.Semaphore(2)
        async with self.preview_slots:
            images, sheet, prompt, manifest = await asyncio.to_thread(extract, paths, settings, edge)
        previews = []
        for image, view in zip(images, manifest["views"]):
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=84)
            previews.append(dict(view, image="data:image/jpeg;base64," +
                                 base64.b64encode(buffer.getvalue()).decode("ascii")))
        return web.json_response({"previews": previews, "prompt": prompt,
                                  "dialogue_prompt": dialogue_prompt(prompt, dict(data, reference_count=len(manifest["views"]))),
                                  "manifest": manifest, "camera": manifest["camera"]})

    async def export(self, request):
        data = await request.json()
        settings = Settings.from_dict(data)
        jobs = data.get("queue", []) if data.get("process_all") else [
            {"path": data["panorama"], "yaw_zero": settings.yaw_zero}]
        if not jobs or len(jobs) > 100:
            raise ValueError("Choose between 1 and 100 sources.")
        if data.get("process_all") and data.get("pair_secondary"):
            raise ValueError("Disable batch mode before exporting a paired capture.")
        prepared = []
        for item in jobs:
            options = dict(data, panorama=item["path"], yaw_zero=item.get("yaw_zero", settings.yaw_zero))
            prepared.append((self.paths(options), Settings.from_dict(options)))
        token = uuid.uuid4().hex
        event = threading.Event()
        state = {"id": token, "status": "queued", "completed_views": 0,
                 "total_views": sum(len(paths) * config.view_count for paths, config in prepared),
                 "packs": [], "error": None, "cancel": event, "created": time.time()}
        self.jobs[token] = state
        # Retain bounded job receipts; never evict a running export.
        for key, value in list(self.jobs.items()):
            if len(self.jobs) > 100 and value["status"] in ("completed", "failed", "cancelled"):
                del self.jobs[key]

        def work():
            def cancel():
                if event.is_set():
                    raise CancelledExport("Export cancelled.")
            state["status"] = "running"
            completed = 0
            try:
                for paths, config in prepared:
                    cancel()
                    def progress(done, total):
                        state["completed_views"] = completed + done
                    _, _, _, _, folder, archive = export_pack(
                        self.output_root, paths, config, cancel=cancel, progress=progress)
                    completed += len(paths) * config.view_count
                    state["packs"].append({
                        "name": folder.name,
                        "url": "/osmo360/download/" + folder.name + "/" + archive.name})
                state["status"] = "completed"
            except CancelledExport:
                state["status"] = "cancelled"
            except Exception as error:
                state["status"] = "failed"
                state["error"] = str(error)
        state["task"] = asyncio.create_task(asyncio.to_thread(work))
        return web.json_response({"id": token, "status": "queued"})

    async def status(self, request):
        state = self.jobs.get(request.match_info["job"])
        if not state:
            raise web.HTTPNotFound()
        return web.json_response({k: v for k, v in state.items() if k not in ("cancel", "task")})

    async def cancel(self, request):
        state = self.jobs.get(request.match_info["job"])
        if not state:
            raise web.HTTPNotFound()
        state["cancel"].set()
        return web.json_response({"status": "cancellation_requested"})

    async def download(self, request):
        folder, name = request.match_info["folder"], request.match_info["name"]
        path = (self.output_root / folder / name).resolve()
        if (not path.is_relative_to(self.output_root) or Path(folder).name != folder
                or Path(name).name != name or path.suffix != ".zip" or not path.is_file()):
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(path.name)})


def install_routes(router, service):
    def wrap(handler):
        async def route(request):
            try:
                return await handler(request)
            except web.HTTPException:
                raise
            except (ValueError, KeyError, TypeError, OSError) as error:
                return web.json_response({"error": str(error)}, status=400)
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Osmo360 request failed")
                return web.json_response({"error": "The extractor service failed. See the Comfy server log."}, status=500)
        return route
    router.post("/osmo360/upload")(wrap(service.upload))
    router.post("/osmo360/preview")(wrap(service.preview))
    router.post("/osmo360/export")(wrap(service.export))
    router.get("/osmo360/jobs/{job}")(wrap(service.status))
    router.post("/osmo360/jobs/{job}/cancel")(wrap(service.cancel))
    router.get("/osmo360/download/{folder}/{name}")(wrap(service.download))


def register_routes():
    try:
        import folder_paths
        from server import PromptServer
    except ImportError:
        return False
    install_routes(PromptServer.instance.routes,
                   Service(folder_paths.get_input_directory(), folder_paths.get_output_directory()))
    return True
