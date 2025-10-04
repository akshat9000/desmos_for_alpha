from dataclasses import dataclass, field
from typing import Set, Dict
from .parser import Number, Name, BinOp, UnaryOp, Call

@dataclass
class Analysis:
    fields: Set[str] = field(default_factory=set)
    windows: Dict[str, Set[int]] = field(default_factory=dict)
    functions: Set[str] = field(default_factory=set)

def _add_window(an: Analysis, field_name: str, n: int):
    an.windows.setdefault(field_name, set()).add(int(n))

def analyze(node) -> Analysis:
    an = Analysis()

    def walk(n):
        if isinstance(n, Name):
            an.fields.add(n.name)

        elif isinstance(n, Call):
            an.functions.add(n.name)

            # crude heuristic: functions with window args
            if n.name in {"ts_mean", "ts_std", "ts_sum", "ts_rank", "delay", "ts_corr", "decay_linear"}:
                if n.args and isinstance(n.args[-1], Number):
                    window = int(n.args[-1].value)
                    if n.args and isinstance(n.args[0], Name):
                        _add_window(an, n.args[0].name, window)

            for a in n.args:
                walk(a)

        elif isinstance(n, (BinOp, UnaryOp)):
            for val in vars(n).values():
                if hasattr(val, "__dict__"):
                    walk(val)

    walk(node)
    return an
