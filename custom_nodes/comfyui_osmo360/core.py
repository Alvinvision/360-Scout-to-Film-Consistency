"""Portable V3 camera geometry and deterministic reference-pack rendering."""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import shutil
import warnings
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC import reports an image-decoder error if this optional dependency is absent.

VERSION = "0.1.0"
PRESETS = {
    "Seedance Landscape": (5, 72, 100, 2048, 1152),
    "Compact Landscape": (4, 90, 110, 2048, 1152),
    "Detailed Landscape": (6, 60, 90, 2048, 1152),
    "Spatial Square": (6, 60, 90, 2048, 2048),
    "Custom": (5, 72, 100, 2048, 1152),
}


@dataclass(frozen=True)
class Settings:
    preset: str = "Seedance Landscape"
    yaw_zero: float = 0
    fov: float = 100
    pitch: float = 0
    roll: float = 0
    projection: str = "Rectilinear"
    strength: float = 100
    width: int = 2048
    height: int = 1152
    view_count: int = 5
    spacing: float = 72
    starting_yaw: float = 0
    upscale: bool = False
    profile: str = "Auto Detect"
    hdr_capture: bool = False
    include_original: bool = False
    location: str = "Location"

    @classmethod
    def from_dict(cls, data):
        valid = set(cls.__dataclass_fields__)
        values = {k: v for k, v in data.items() if k in valid}
        obj = cls(**values)
        obj.validate()
        return obj

    def validate(self):
        if self.preset not in PRESETS:
            raise ValueError("Unknown reference preset.")
        if self.projection not in ("Rectilinear", "Natural Wide"):
            raise ValueError("Choose Rectilinear or Natural Wide.")
        if not all(math.isfinite(float(getattr(self, k))) for k in
                   ("yaw_zero", "fov", "pitch", "roll", "strength", "spacing", "starting_yaw")):
            raise ValueError("Camera settings must be finite numbers.")
        if not 1 < self.fov < 179 or not 0 <= self.strength <= 100:
            raise ValueError("FOV must be between 1 and 179 degrees; strength between 0 and 100.")
        if abs(self.pitch) > 90 or abs(self.roll) > 180:
            raise ValueError("Pitch must be within ±90 degrees and roll within ±180.")
        if not (isinstance(self.width, int) and isinstance(self.height, int)
                and 16 <= self.width <= 8192 and 16 <= self.height <= 8192):
            raise ValueError("Output dimensions must be integers between 16 and 8192.")
        if not isinstance(self.view_count, int) or not 1 <= self.view_count <= 24:
            raise ValueError("View count must be an integer from 1 to 24.")
        names = [yaw_name((self.starting_yaw + i * self.spacing) % 360)
                 for i in range(self.view_count)]
        if len(names) != len(set(names)):
            raise ValueError("Camera spacing produces duplicate yaw filenames.")

    @property
    def compression(self):
        return self.strength / 100 if self.projection == "Natural Wide" else 0.0

    @property
    def vertical_fov(self):
        return math.degrees(2 * math.atan(half_width(self.fov, self.compression)
                                         * self.height / self.width))


def half_width(fov, d):
    angle = math.radians(fov / 2)
    return (d + 1) * math.sin(angle) / (d + math.cos(angle))


def yaw_name(yaw):
    return "%03d" % (math.floor((yaw % 360) + 0.5) % 360)


def safe_name(name):
    return re.sub(r"[^\w.-]+", "_", str(name), flags=re.UNICODE).strip("._")[:100] or "Location"


def classify(width, height):
    if width <= 0 or height <= 0 or abs(width / height - 2) > 0.08:
        raise ValueError("Spherical extraction requires an approximately 2:1 stitched panorama.")
    mp = width * height / 1_000_000
    if 12000 <= width <= 18500 and 6000 <= height <= 9250 and 75 <= mp <= 170:
        return "120MP DETAIL"
    if 5500 <= width <= 10000 and 2750 <= height <= 5000 and 18 <= mp <= 52:
        return "30MP PANORAMA"
    return "360 PANORAMA"


def metadata(path):
    path = Path(path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        # Pillow's default warning threshold is below a valid 120MP Osmo still.
        with Image.open(path) as im:
            width, height = im.size
            if width * height > 200_000_000:
                raise ValueError("Panorama exceeds this port's 200MP decode limit.")
            orientation = im.getexif().get(274, 1)
            if orientation in (5, 6, 7, 8):
                width, height = height, width
            profile = classify(width, height)
            return {"filename": path.name, "width": width, "height": height,
                    "profile": profile, "hdr_status": "unknown",
                    "hdr_evidence": None, "orientation": orientation,
                    "projection": "equirectangular"}


def read_source(path, preview=False):
    meta = metadata(path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        with Image.open(path) as original:
            if preview:
                original.draft("RGB", (4096, 2048))
            image = ImageOps.exif_transpose(original)
            if preview:
                image.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
            profile_bytes = original.info.get("icc_profile")
            if profile_bytes:
                from PIL import ImageCms
                image = ImageCms.profileToProfile(
                    image, ImageCms.ImageCmsProfile(io.BytesIO(profile_bytes)),
                    ImageCms.createProfile("sRGB"), outputMode="RGB")
            array = np.array(image.convert("RGB"))
    return array, meta


def effective_settings(settings, metas):
    settings.validate()
    if settings.upscale:
        return settings
    caps = []
    for index, meta in enumerate(metas):
        # The primary's manual profile must never override a 30MP pair member.
        profile = settings.profile if index == 0 and settings.profile != "Auto Detect" else meta["profile"]
        if profile == "120MP DETAIL":
            cap = 4096
        elif profile in ("30MP PANORAMA", "30MP HDR"):
            cap = 2048
        else:
            cap = max(256, min(4096, math.floor(min(
                meta["width"] * settings.fov / 360,
                meta["height"] * settings.vertical_fov / 180))))
        caps.append(cap)
    scale = min(1, min(caps) / max(settings.width, settings.height))
    return replace(settings, width=max(16, math.floor(settings.width * scale + 0.5)),
                   height=max(16, math.floor(settings.height * scale + 0.5)))


def camera_plan(settings):
    settings.validate()
    yaws = [(settings.starting_yaw + i * settings.spacing) % 360
            for i in range(settings.view_count)]
    ordered = sorted(yaws)
    gaps = [(ordered[(i + 1) % len(ordered)] - yaw) % 360 for i, yaw in enumerate(ordered)]
    overlaps = [max(0, settings.fov - gap) for gap in gaps] if len(yaws) > 1 else []
    uniform = not gaps or max(gaps) - min(gaps) < 1e-6
    cameras = []
    for i, yaw in enumerate(yaws):
        previous = min(((yaw - y) % 360 for y in yaws if y != yaw), default=360)
        following = min(((y - yaw) % 360 for y in yaws if y != yaw), default=360)
        cameras.append({"index": i, "relativeYaw": yaw,
                        "sourceYaw": (settings.yaw_zero + yaw) % 360,
                        "pitch": settings.pitch, "roll": settings.roll,
                        "horizontalFOV": settings.fov, "verticalFOV": settings.vertical_fov,
                        "width": settings.width, "height": settings.height,
                        "projectionStyle": settings.projection,
                        "overlapLeft": max(0, settings.fov - previous) if len(yaws) > 1 else 0,
                        "overlapRight": max(0, settings.fov - following) if len(yaws) > 1 else 0,
                        "bandLeft": overlap_fraction(settings, previous),
                        "bandRight": overlap_fraction(settings, following)})
    return cameras, overlaps, uniform


def overlap_fraction(settings, gap):
    boundary = gap - settings.fov / 2
    if boundary >= settings.fov / 2:
        return 0.0
    if boundary <= -settings.fov / 2:
        return 0.5
    d = settings.compression
    angle = math.radians(boundary)
    x = (d + 1) * math.sin(angle) / (d + math.cos(angle))
    return max(0, min(0.5, (1 - x / half_width(settings.fov, d)) / 2))


def source_coordinates(settings, camera, width, height, first_row=0, last_row=None):
    """V3 raster sampling in a top-left image; rotate roll, pitch, then yaw.

    Core Image destCoord() already addresses the pixel centre; V3 adds 0.5
    again. Its x sample is therefore x+1 and its top-origin y sample is y.
    Preserve that raster convention for parity instead of silently recentering.
    """
    last_row = height if last_row is None else last_row
    extent = half_width(settings.fov, settings.compression)
    x = ((np.arange(width, dtype=np.float64) + 1.0) / width * 2 - 1)[None, :] * extent
    y = (1 - np.arange(first_row, last_row, dtype=np.float64) / height * 2)[:, None]
    y = y * extent * height / width
    if settings.compression:
        d = settings.compression
        k = x * x / (d + 1) ** 2
        cosine = np.clip((-k * d + np.sqrt(np.maximum(0, 1 + k * (1 - d * d)))) / (1 + k), -1, 1)
        sine = x * (d + cosine) / (d + 1)
        tangent = y * (d + cosine) / (d + 1)
        cos_phi = 1 / np.sqrt(1 + tangent * tangent)
        x, y, z = sine * cos_phi, tangent * cos_phi, cosine * cos_phi
    else:
        z = np.ones_like(x + y)
    roll, pitch, yaw = map(math.radians, (camera["roll"], camera["pitch"], camera["sourceYaw"]))
    rx, ry = math.cos(roll) * x - math.sin(roll) * y, math.sin(roll) * x + math.cos(roll) * y
    py, pz = math.cos(pitch) * ry + math.sin(pitch) * z, -math.sin(pitch) * ry + math.cos(pitch) * z
    dx, dz = math.cos(yaw) * rx + math.sin(yaw) * pz, -math.sin(yaw) * rx + math.cos(yaw) * pz
    magnitude = np.sqrt(dx * dx + py * py + dz * dz)
    return ((0.5 + np.arctan2(dx, dz) / (2 * math.pi)) % 1,
            np.clip(0.5 - np.arcsin(np.clip(py / magnitude, -1, 1)) / math.pi, 0, 1))


def _linear(value):
    value = value.astype(np.float32) / 255
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def render(source, settings, camera, width=None, height=None, cancel=None):
    width, height = width or settings.width, height or settings.height
    sh, sw = source.shape[:2]
    output = np.empty((height, width, 3), dtype=np.uint8)
    for top in range(0, height, 64):
        if cancel:
            cancel()
        bottom = min(height, top + 64)
        u, v = source_coordinates(settings, camera, width, height, top, bottom)
        sx, sy = u * sw - 0.5, np.clip(v * sh - 0.5, 0, sh - 1)
        x0, y0 = np.floor(sx).astype(np.int64), np.floor(sy).astype(np.int64)
        ax, ay = (sx - x0)[..., None], (sy - y0)[..., None]
        x1, y1 = (x0 + 1) % sw, np.minimum(y0 + 1, sh - 1)
        x0 %= sw
        a = _linear(source[y0, x0]) * (1 - ax) + _linear(source[y0, x1]) * ax
        b = _linear(source[y1, x0]) * (1 - ax) + _linear(source[y1, x1]) * ax
        rgb = np.clip(a * (1 - ay) + b * ay, 0, 1)
        rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
        output[top:bottom] = np.clip(np.floor(rgb * 255 + 0.5), 0, 255).astype(np.uint8)
    return Image.fromarray(output)


def grid_rows(count):
    if count <= 3:
        return [count]
    if count == 4:
        return [2, 2]
    if count == 5:
        return [3, 2]
    columns = min(6, math.ceil(math.sqrt(count)))
    return [min(columns, count - i) for i in range(0, count, columns)]


def contact_sheet(images, views, settings, overlay=True):
    thumb_width = 480
    thumb_height = round(thumb_width * settings.height / settings.width)
    rows = grid_rows(len(images))
    gap, caption, margin = 18, 62, 24
    width = max(rows) * (thumb_width + gap) - gap + margin * 2
    height = 90 + len(rows) * (thumb_height + caption + gap) + 50
    sheet = Image.new("RGB", (width, height), "#111820")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 18), settings.location + " / CONTINUOUS 360 REFERENCE", fill="white")
    draw.text((margin, 42), "%s / %s / HFOV %.1f / VFOV %.1f / %dx%d" %
              (settings.preset, settings.projection, settings.fov, settings.vertical_fov,
               settings.width, settings.height), fill="#a9c7df")
    index, y = 0, 90
    for row in rows:
        x = (width - row * (thumb_width + gap) + gap) // 2
        for _ in range(row):
            view = views[index]
            tile = images[index].resize((thumb_width, thumb_height), Image.Resampling.LANCZOS).convert("RGBA")
            if overlay:
                shade = Image.new("RGBA", tile.size)
                painter = ImageDraw.Draw(shade)
                painter.rectangle((0, 0, int(thumb_width * view["bandLeft"]), thumb_height), fill=(120, 190, 245, 40))
                painter.rectangle((int(thumb_width * (1 - view["bandRight"])), 0, thumb_width, thumb_height), fill=(120, 190, 245, 40))
                tile = Image.alpha_composite(tile, shade)
            sheet.paste(tile.convert("RGB"), (x, y))
            draw.text((x, y + thumb_height + 8), view["filename"], fill="white")
            draw.text((x, y + thumb_height + 26), "Yaw %s / HFOV %.1f / VFOV %.1f" %
                      (yaw_name(view["relativeYaw"]), settings.fov, settings.vertical_fov), fill="#b8cbd8")
            draw.text((x, y + thumb_height + 42), "Pitch %.1f / Roll %.1f / Overlap L %.1f R %.1f" %
                      (settings.pitch, settings.roll, view["overlapLeft"], view["overlapRight"]), fill="#b8cbd8")
            index += 1
            x += thumb_width + gap
        y += thumb_height + caption + gap
    draw.text((margin, height - 30), "Shading appears only on this review sheet. Individual PNG references are clean.", fill="#b8cbd8")
    return sheet


def reference_prompt(views, settings):
    kind = "rectilinear" if settings.projection == "Rectilinear" else "General Panini reduced-edge-stretch"
    files = "\n".join("%s — relative yaw %.1f degrees" % (v["filename"], v["relativeYaw"]) for v in views)
    return ("These %d overlapping %s perspective images show ONE continuous physical environment "
            "from ONE camera position and height, rotating around that position.\n\n%s\n\n"
            "Horizontal FOV %.2f degrees; delivered vertical FOV %.2f degrees; pitch %.2f; roll %.2f. "
            "Repeated walls, doors, vehicles, plants and landmarks are the SAME objects. "
            "Preserve their identities, relative positions, materials and lighting across shots. "
            "Do not mirror the location or duplicate its architecture. "
            "These views are not a calibrated 3D reconstruction; camera translations require inference."
            % (len(views), kind, files, settings.fov, settings.vertical_fov, settings.pitch, settings.roll))


def extract(paths, settings, preview_edge=None, cancel=None, progress=None):
    if not paths or len(paths) > 2:
        raise ValueError("Choose one panorama, or one explicitly paired capture.")
    metas = [metadata(path) for path in paths]
    for index, meta in enumerate(metas):
        meta["sourceProfile"] = settings.profile if index == 0 and settings.profile != "Auto Detect" else meta["profile"]
        if settings.hdr_capture and (len(paths) == 1 or index == 1):
            meta["hdr_status"] = "user-marked"
    actual = effective_settings(settings, metas)
    cameras, overlaps, uniform = camera_plan(actual)
    base = safe_name(actual.location)
    images, views = [], []
    for source_index, path in enumerate(paths):
        source, _ = read_source(path, preview=preview_edge is not None)
        role = "" if len(paths) == 1 else ("DETAIL" if source_index == 0 else ("HDR" if actual.hdr_capture else "PANORAMA"))
        for camera in cameras:
            if cancel:
                cancel()
            view = dict(camera, sourceIndex=source_index, role=role)
            view["filename"] = base + "_" + yaw_name(view["relativeYaw"]) + ("_" + role if role else "") + ".png"
            if preview_edge:
                scale = min(1, preview_edge / max(actual.width, actual.height))
                width, height = max(2, round(actual.width * scale)), max(2, round(actual.height * scale))
            else:
                width, height = actual.width, actual.height
            images.append(render(source, actual, camera, width, height, cancel))
            views.append(view)
            if progress:
                progress(len(views), len(paths) * len(cameras))
        del source
    manifest = {"schemaVersion": 1, "applicationName": "Osmo360 ComfyUI",
                "applicationVersion": VERSION, "geometryBaseline": "360 Reference Extractor V3 3.0 build 3",
                "camera": asdict(actual), "views": views, "sources": metas,
                "neighborOverlaps": overlaps, "uniformYawSpacing": uniform,
                "pairedCapture": len(paths) == 2,
                "hdrStatus": "user-marked" if actual.hdr_capture else "unknown",
                "hdrDetection": "Embedded Apple gain-map recognition is not implemented in this port."}
    return images, contact_sheet(images, views, actual), reference_prompt(views, actual), manifest


def export_pack(output_root, paths, settings, cancel=None, progress=None):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    base = safe_name(settings.location)
    folder, counter = output_root / base, 1
    while True:
        try:
            folder.mkdir()
            break
        except FileExistsError:
            counter += 1
            folder = output_root / (base + "_" + str(counter))
    try:
        images, sheet, prompt, manifest = extract(paths, settings, cancel=cancel, progress=progress)
        for image, view in zip(images, manifest["views"]):
            if cancel:
                cancel()
            image.save(folder / view["filename"], format="PNG")
        sheet.save(folder / (base + "_CONTACTSHEET.jpg"), quality=92)
        (folder / (base + "_REFERENCE_PROMPT.txt")).write_text(prompt, encoding="utf-8")
        for path, meta in zip(paths, manifest["sources"]):
            digest = hashlib.sha256()
            with Path(path).open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            meta["sha256"] = digest.hexdigest()
            if settings.include_original:
                original_dir = folder / "ORIGINALS"
                original_dir.mkdir(exist_ok=True)
                target = original_dir / (str(len(list(original_dir.iterdir()))) + "_" + Path(path).name)
                shutil.copy2(path, target)
                meta["originalCopy"] = str(target.relative_to(folder))
        (folder / (base + "_manifest.json")).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        archive = folder / (base + "_REFERENCE_PACK.zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(folder.rglob("*")):
                if path.is_file() and path != archive:
                    z.write(path, path.relative_to(folder))
        return images, sheet, prompt, manifest, folder, archive
    except BaseException:
        # Keep a visible receipt for a cancelled/failed export; never call it complete.
        (folder / "INCOMPLETE.txt").write_text("Export did not complete. Do not use this folder as a complete pack.")
        raise


def dialogue_prompt(location_prompt, options):
    """Ten seconds: establishing pan, two three-quarter OTS shots, continuous axis crossing."""
    wide = float(options.get("wide_fov", 70))
    ots = float(options.get("ots_fov", 50))
    height = float(options.get("camera_height", 1.6))
    crossing = float(options.get("cross_fov", 60))
    yaw = float(options.get("scene_yaw", 216)) % 360
    count = int(options.get("reference_count", options.get("view_count", 5)))
    if not 1 <= count <= 48:
        raise ValueError("The dialogue prompt requires between 1 and 48 location references.")
    if not all(math.isfinite(v) for v in (wide, ots, crossing, height, yaw)) or not (10 <= wide <= 150 and 10 <= ots <= 150 and 10 <= crossing <= 150 and 0.3 <= height <= 3):
        raise ValueError("Choose valid FOV values and a camera height from 0.3 to 3 metres.")
    return (location_prompt + "\n\n"
            "CAST: Image %d is Brais: ONE man shown in front/detail/back views on one identity sheet; "
            "short dark hair, moustache, dark jacket, light T-shirt, dark trousers and boots. "
            "Image %d is Noa: ONE woman shown in front/detail/back views; close-cropped hair, "
            "grey overshirt, grey top, dark trousers and boots. Match their reference faces and clothing. "
            "Use the sheets only for identity and wardrobe, not their white studio backgrounds.\n\n"
            "BLOCKING: Place Brais and Noa facing one another about 1.5 metres apart on the existing paved "
            "forecourt outside the brick workshop. Brais is nearer the building; Noa is nearer the road. "
            "They remain on those marks in every shot. The line between them is the dialogue axis. "
            "The building, road, containers, vehicles and vegetation keep their real relationships.\n\n"
            "Create ONE 10-second video containing EXACTLY FOUR shots. The actors, their marks, and the "
            "location remain continuous across the whole sequence. Hard cuts separate shots 1, 2, 3 and 4; "
            "there is no additional cut inside any shot.\n"
            "SHOT 1, 0–3 seconds — Establish both performers in the middle of the frame on the real forecourt, looking approximately toward "
            "relative panorama yaw %.1f degrees with a %.1f-degree horizontal FOV. "
            "Make a controlled pan with a short lateral arc, revealing the workshop entrance, brick facade "
            "and adjacent road while keeping both performers in central framing. Show enough background to establish the geography.\n"
            "SHOT 2, 3–5 seconds — Hard cut to a three-quarter over-Brais-shoulder view of Noa, "
            "from behind and slightly to the side of Brais. Brais's matching dark jacket "
            "and back of head form one foreground shoulder, while Noa's face is clearly visible and her "
            "eyeline reaches Brais. Use approximately %.1f-degree horizontal FOV at %.2fm camera height.\n"
            "SHOT 3, 5–7 seconds — Hard cut to a matching three-quarter reverse over-Noa-shoulder "
            "view of Brais, from behind and slightly to the side of Noa. Noa's matching grey shoulder and close-cropped head are in the foreground; "
            "Brais's face and moustache are clearly visible. Use the same %.1f-degree FOV and %.2fm height. "
            "The corresponding side of the captured environment is visible with correct landmark relationships.\n"
            "SHOT 4, 7–10 seconds — Cut into one uninterrupted, smooth camera arc that visibly crosses the "
            "physical dialogue axis between the two fixed performers. Use approximately %.1f-degree horizontal "
            "FOV. Let the changing foreground shoulders, eyelines and rotating background reveal that the camera "
            "has moved to the opposite side. There is NO cut or teleportation within shot 4. "
            "The camera changes sides; the performers never swap positions. Brickwork, workshop opening, road, "
            "containers and vehicles remain the same objects in the same places throughout the arc. "
            "As the crossing completes, continue the same unbroken move into a concluding pan around the "
            "location, revealing the surrounding workshop, road, containers and vegetation so the environment "
            "is clearly readable at the end. This concluding pan belongs to shot 4; do not add a fifth shot.\n\n"
            "Keep the photographed daylight, scale and materials coherent across all three cuts. Natural restrained "
            "performance and a small breeze, silent scene. Maintain exactly two performers with consistent "
            "identity, wardrobe and eyelines. Render full-frame images, not a collage or reference sheet. "
            "The output contains four shots, not three and not a single uncut take."
            % (count + 1, count + 2, yaw, wide, ots, height, ots, height, crossing))
