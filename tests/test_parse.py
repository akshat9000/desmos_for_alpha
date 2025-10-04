
import pytest
from dsl.parser import parse_alpha

@pytest.mark.parametrize("src", [
    "1+2*3",
    "rank(ts_mean(returns,5))",
    "if(a>0, a, -a)",
    "ts_mean(returns, 10) - ts_mean(returns, 20)",
    "sdiv(1, 0)",
    "zscore(close)",
])
def test_parse_ok(src):
    ast = parse_alpha(src)
    assert ast is not None
