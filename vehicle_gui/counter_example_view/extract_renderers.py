import importlib.util
import inspect
from typing import Type
from pathlib import Path
from ui.counter_example_view.base_renderer import BaseRenderer


def load_renderer_classes(path: str) -> list[Type[BaseRenderer]]:
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    renderers = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseRenderer) and obj is not BaseRenderer:
            renderers.append(obj())
    return renderers


def initialise_custom_renderers(path: str) -> list[BaseRenderer]:
    renderer_classes = load_renderer_classes(path)
    renderer_objects = []
    
    for Renderer in renderer_classes:
        renderer_objects.append(Renderer())
        
    return renderer_objects