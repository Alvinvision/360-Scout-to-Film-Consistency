"""Loopback-only QA harness for the exact frontend module shipped in the pack."""
import argparse
import json
import shutil
import sys
from pathlib import Path
from aiohttp import web

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK.parent))
from comfyui_osmo360.core import Settings, metadata
from comfyui_osmo360.routes import Service, install_routes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--panorama", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--talent-a", type=Path)
    parser.add_argument("--talent-b", type=Path)
    args = parser.parse_args()
    source_root = args.data / "input"
    source_root.mkdir(parents=True, exist_ok=True)
    target = source_root / args.panorama.name
    if not target.exists():
        shutil.copy2(args.panorama, target)
    settings = Settings(location="L001").__dict__.copy()
    settings["panorama"] = target.name
    settings.update(pair_secondary="", pair_same_position=False, process_all=False,
                    scene_yaw=216, wide_fov=70, ots_fov=50, cross_fov=60, camera_height=1.6)
    for option, key in [(args.talent_a, "talent_a"), (args.talent_b, "talent_b")]:
        if option:
            dest = source_root / option.name
            if not dest.exists():
                shutil.copy2(option, dest)
            settings[key] = dest.name
    queue = [dict(metadata(target), path=target.name, display_name=target.name, yaw_zero=0)]
    settings["queue_json"] = json.dumps(queue)
    service = Service(source_root, args.data / "output")
    routes = web.RouteTableDef()
    install_routes(routes, service)

    @routes.get("/")
    async def index(request):
        html = """<!doctype html><html><head><meta charset="utf-8"><title>Osmo360 custom frontend QA</title>
<style>html,body{margin:0;height:100%;background:#17191d}#qa{height:100%}</style></head><body>
<div id="qa"></div><script type="module">
import {mountExtractor} from '/js/extractor_ui_v2.js';
const response=await fetch('/qa/bootstrap');const data=await response.json();
let state=data.settings,queue=data.queue;
mountExtractor(document.querySelector('#qa'),{
get:()=>state,set:values=>Object.assign(state,values),
getQueue:()=>queue,setQueue:values=>{queue=values;},
fetch:(path,options)=>fetch(path,options)
});
</script></body></html>"""
        return web.Response(text=html, content_type="text/html")

    @routes.get("/qa/bootstrap")
    async def bootstrap(request):
        return web.json_response({"settings": settings, "queue": queue})

    app = web.Application(client_max_size=500 * 1024 ** 2)
    app.add_routes(routes)
    app.router.add_static("/js", PACK / "js")
    web.run_app(app, host="127.0.0.1", port=args.port, print=lambda msg: print(msg, flush=True))


if __name__ == "__main__":
    main()
