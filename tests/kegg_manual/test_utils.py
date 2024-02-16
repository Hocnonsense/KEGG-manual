# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-16 11:59:29
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 11:59:30
 * @FilePath: /KEGG/tests/kegg_manual/test_utils.py
 * @Description:
"""
# """

from kegg_manual.utils import Variable as V


def test_variable():
    for s in ("xyz", "x2", "x_y", "\u00c6\u00d8\u00c5", "x12345.6", "123"):
        v = V(s)
        assert str(v) == s
        assert v.symbol == s

    for s in ("xyz", "x2", "x_y", "\u00c6\u00d8\u00c5"):
        v = V(s, strict=True)
    for s in ("x12345.6", "123", "x "):
        try:
            v = V(s, strict=True)
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
    assert V("x").substitute(lambda v: {"y": 42}.get(v.symbol, v)) == V("x")
    assert V("x").substitute(lambda v: {"x": 123, "y": 56}.get(v.symbol, v)) == 123
