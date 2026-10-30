from .nodes import Osmo360DialoguePrompt, Osmo360ReferencePack, Osmo360SelectView, Osmo360PanoramaInput

NODE_CLASS_MAPPINGS = {
    "Osmo360PanoramaInput": Osmo360PanoramaInput,
    "Osmo360ReferencePack": Osmo360ReferencePack,
    "Osmo360SelectView": Osmo360SelectView,
    "Osmo360DialoguePrompt": Osmo360DialoguePrompt,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "Osmo360PanoramaInput": "Osmo 360 Original Panorama / Upload and Swap",
    "Osmo360ReferencePack": "Osmo 360 Reference Extractor",
    "Osmo360SelectView": "Osmo 360 Select Reference View",
    "Osmo360DialoguePrompt": "Osmo 360 Dialogue and Reverse OTS Prompt",
}
WEB_DIRECTORY = "./js"

# The standalone test harness uses the same routes, but supplies its own roots.
from .routes import register_routes
register_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
