"""Testable PEFT state contract, shared by real serving and offline doubles."""
from contextlib import contextmanager,nullcontext

def assert_selected(layers,arm):
    if arm not in ('V','N','U') or not layers:raise ValueError('Unknown arm/empty adapter inventory')
    for _,layer in layers:
        if arm=='U':
            if not layer.disable_adapters:raise ValueError('U has an active adapter')
        elif layer.disable_adapters or list(layer.active_adapters)!=[arm]:raise ValueError('Adapter inactive, swapped or contaminated')

@contextmanager
def selection(model,layers,arm):
    if arm not in ('V','N','U'):raise ValueError('Unknown treatment; no base fallback')
    previous=[(bool(l.disable_adapters),list(l.active_adapters)) for _,l in layers]
    if arm!='U':model.set_adapter(arm)
    context=model.disable_adapter() if arm=='U' else nullcontext()
    try:
        with context:
            assert_selected(layers,arm)
            yield
            assert_selected(layers,arm)
    finally:
        if arm=='U' and [(bool(l.disable_adapters),list(l.active_adapters)) for _,l in layers]!=previous:
            raise ValueError('U context leaked disabled/active state')
