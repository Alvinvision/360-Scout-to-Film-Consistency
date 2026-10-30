from .nodes import LocationReferenceImage, Osmo360DialoguePrompt, Osmo360ReferencePack, Osmo360SelectView, Osmo360PanoramaInput

NODE_CLASS_MAPPINGS = {
    "LocationReferenceImage": LocationReferenceImage,
    "Osmo360PanoramaInput": Osmo360PanoramaInput,
    "Osmo360ReferencePack": Osmo360ReferencePack,
    "Osmo360SelectView": Osmo360SelectView,
    "Osmo360DialoguePrompt": Osmo360DialoguePrompt,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "LocationReferenceImage": "Image Reference / Upload",
    "Osmo360PanoramaInput": "360 Location / Original Panorama",
    "Osmo360ReferencePack": "360 Location Extractor",
    "Osmo360SelectView": "360 Location / Select Reference View",
    "Osmo360DialoguePrompt": "Video / Dialogue and Reverse OTS Prompt",
}
WEB_DIRECTORY = "./js"

# The standalone test harness uses the same routes, but supplies its own roots.
from .routes import register_routes
register_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
