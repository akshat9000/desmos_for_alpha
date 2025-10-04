
from typing import Callable, Dict, NamedTuple, Iterable, Union, List

class FuncSpec(NamedTuple):
    name: str
    arity: Union[range, List[int]]
    impl: Callable
    kind: str       # "ts" | "cs" | "scalar"
    doc: str

REGISTRY: Dict[str, FuncSpec] = {}

def register(name, arity, kind, doc=""):
    def deco(fn):
        REGISTRY[name] = FuncSpec(name, arity, fn, kind, doc)
        return fn
    return deco

def get_fn(name: str) -> FuncSpec:
    if name not in REGISTRY:
        raise KeyError(f"Unknown function '{name}'")
    return REGISTRY[name]

def list_functions():
    out = []
    for k, spec in sorted(REGISTRY.items()):
        arity = list(spec.arity) if isinstance(spec.arity, range) else spec.arity
        out.append({"name": k, "arity": arity, "kind": spec.kind, "doc": spec.doc})
    return out
