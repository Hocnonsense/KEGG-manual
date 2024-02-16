# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-16 11:59:29
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 22:04:21
 * @FilePath: /KEGG/tests/kegg_manual/test_utils.py
 * @Description:
"""
# """

from kegg_manual.utils import Variable as V
from kegg_manual.utils import LineExpression as E
from kegg_manual.utils import ParseError


def test_variable():
    for s in ("xyz", "x2", "x_y", "\u00c6\u00d8\u00c5", "x12345.6", "123"):
        v = V(s)
        assert str(v) == s
        assert v.symbol == s, "symbol"
        assert v.simplify() == v, "simplify_returns_self"

    for s in ("xyz", "x2", "x_y", "\u00c6\u00d8\u00c5"):
        v = V(s, symbol_strict=True)
    for s in ("x12345.6", "123", "x ", "45x"):
        try:
            v = V(s, symbol_strict=True)
        except ValueError:
            pass
        else:
            assert False


def test_variables_equals():
    assert V("x") == V("x")
    assert V("x") != V("y")
    assert V("x") != True
    assert hash(V("xyz")) == hash(V("xyz"))


def test_variables_substitute():
    assert V("x").substitute(lambda v: {"x": 567}.get(v.symbol, v)) == 567
    assert V("x").substitute(lambda v: {"y": 42}.get(v.symbol, v)) == V("x"), "unknown"
    assert (
        V("x").substitute(lambda v: {"x": 123, "y": 56}.get(v.symbol, v)) == 123
    ), "multiple"


def test_variables_sort():
    names = ("b", "cd", "a", "cc")
    vars = sorted(V(i) for i in names)
    assert vars == [V(i) for i in sorted(names)]


def test_variables_hash():
    assert hash(V("x")) == hash(V("x"))


def test_expression():
    assert str(E()) == "0"
    assert str(E({V("x"): 1}, 1)) == "x + 1"
    assert str(E({V("a"): 1, V("b"): 2})) == "a + 2b"
    assert str(E({}, -3)) == "-3"


def test_expression_neq():
    assert E({}, 5) == 5
    assert E({}, 5) != -5

    assert E({V("a"): 1}) == V("a")
    assert E({V("a"): 1}) != 3

    assert E({V("a"): 4}, 5) == E({V("a"): 4, V("b"): 0}, 5)
    assert E({V("a"): 4, V("b"): 1}, 5) == E({V("a"): 4, V("b"): 1}, 5)

    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("b"): 4, V("a"): 1}, 5)
    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("a"): 4}, 5)
    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("a"): 4, V("b"): 1})
    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("a"): 4, V("b"): 2}, 5)
    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("a"): 4, V("b"): -1}, 5)
    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("a"): 4, V("b"): 1}, -5)
    assert E({V("a"): 4, V("b"): 1}, 5) != E({V("a"): -4, V("b"): -1}, -5)


def test_expression_value():
    try:
        E({"a": 2})  # type: ignore [dict-item]
    except ValueError:
        pass
    else:
        assert False

    assert list(E({V("x"): 1, V("y"): 2}).variables()) == [V("x"), V("y")]


def test_expression_add():
    assert E() + E() == E()
    assert E() - 1 == E({}, -1)
    assert E({V("x"): 2}) + E() == E({V("x"): 2})
    assert E({V("x"): 2}) + E({V("x"): 2}, 1) == E({V("x"): 4}, 1)
    assert E({V("x"): 2}) - E({V("x"): 2}, 1) == E({}, -1)
    assert E({V("x"): 2}) + E({V("y"): 2, V("x"): -2}) == E({V("y"): 2})
    assert 4 - E({V("x"): 2}) == E({V("x"): -2}, 4)
    e = E({V("x"): 2})
    assert e - e == E()


def test_variables_add():
    assert V("x") + 1 == E({V("x"): 1}, 1)
    assert 1 + V("x") == E({V("x"): 1}, 1)
    assert V("x") - 4 == E({V("x"): 1}, -4)
    assert 4 - V("x") == E({V("x"): -1}, 4)


def test_variables_mul():
    assert V("x") * 0 == 0
    assert V("x") * 1 == V("x")
    assert V("x") * 2 == E({V("x"): 2})
    assert 3 * V("x") == E({V("x"): 3})
    assert V("x") / 0.25 == E({V("x"): 4})

    assert -V("x") == E({V("x"): -1})


def test_expression_simplify():
    result = E({}, 5).simplify()
    assert result == 5 and isinstance(result, int)
    result = E({V("x"): 1}).simplify()
    assert result == V("x") and isinstance(result, V)
    result = E({V("x"): 2}).simplify()
    assert result == E({V("x"): 2}) and isinstance(result, E)
    result = E({V("x"): 2}, 1).simplify()
    assert result == E({V("x"): 2}, 1) and isinstance(result, E)


def test_expression_substitute():
    e = E({V("x"): 2}, 1)
    assert e.substitute(lambda v: {"x": 2}.get(v.symbol, v)) == 5
    assert e.substitute(lambda v: v) == e
    e = E({V("x"): 1})
    assert e.substitute(lambda v: v) == V("x")
    e = E({V("x"): 1, V("y"): 2})
    assert e.substitute(lambda v: {"y": V("x")}.get(v.symbol, v)) == E({V("x"): 3})
    e = E({V("x"): 3, V("y"): -2})
    assert e.substitute(
        lambda v: {"x": E({V("z"): 2, V("y"): 1})}.get(v.symbol, v)
    ) == E({V("z"): 6, V("y"): 1})
    e = E({V("x"): 1, V("y"): 1})
    assert e.substitute(lambda v: {"x": e, "y": e}.get(v.symbol, v)) == E(
        {V("x"): 2, V("y"): 2}
    )


def test_ParseError():
    e = ParseError("This is an error", span=(4, 7))
    assert e.indicator == "    ^^^"

    e = ParseError("This is an error")
    assert e.indicator is None
