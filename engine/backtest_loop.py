import pandas as pd
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node

def evaluate_series(alpha_src: str, fields: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute alpha value per date × symbol using current eval_node.
    (v0: simple date-loop; v1 will use vectorized rolling.)
    """
    ast = parse_alpha(alpha_src)
    dates = next(iter(fields.values())).index
    results = []
    for t in dates:
        ctx = EvaluationContext(fields, t)
        s = eval_node(ctx, ast)
        s.name = t
        results.append(s)
    return pd.DataFrame(results, index=dates)
