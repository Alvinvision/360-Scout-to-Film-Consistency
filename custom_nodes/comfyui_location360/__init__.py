from .nodes import LocationReferenceImage, Location360DialoguePrompt, Location360ReferencePack, Location360SelectView, Location360PanoramaInput

NODE_CLASS_MAPPINGS = {
    "LocationReferenceImage": LocationReferenceImage,
    "Location360PanoramaInput": Location360PanoramaInput,
    "Location360ReferencePack": Location360ReferencePack,
    "Location360SelectView": Location360SelectView,
    "Location360DialoguePrompt": Location360DialoguePrompt,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "LocationReferenceImage": "Image Reference / Upload",
    "Location360PanoramaInput": "360 Location / Original Panorama",
    "Location360ReferencePack": "360 Location Extractor",
    "Location360SelectView": "360 Location / Select Reference View",
    "Location360DialoguePrompt": "Video / Dialogue and Reverse OTS Prompt",
}
WEB_DIRECTORY = "./js"

# The standalone test harness uses the same routes, but supplies its own roots.
from .routes import register_routes
register_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
