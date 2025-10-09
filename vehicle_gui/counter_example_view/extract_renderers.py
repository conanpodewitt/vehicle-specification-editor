import importlib.util
import inspect
from typing import Type
from pathlib import Path
from vehicle_gui.counter_example_view.base_renderer import BaseRenderer


def load_renderer_classes(path: str) -> list[Type[BaseRenderer]]:
    """Load renderer class types from a Python file without instantiating them."""
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    renderer_classes = []

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseRenderer) and obj is not BaseRenderer:
            renderer_classes.append(obj)

    return renderer_classes