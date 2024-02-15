# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-16 00:03:38
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 00:11:09
 * @FilePath: /KEGG/tests/kegg_manual/expression/test_boolean.py
 * @Description:
"""
# """


from kegg_manual.expression import boolean


def test_variable():
    v = boolean.Variable("v")
    assert str(v) == "v"
    assert v.symbol == "v"


def test_expression():
    s = "a and (b or c)"
    e = boolean.Expression(s)
    e._root
    assert str(e.root) == s
    assert str(e) == s


def test__parse_expression():
    s = "a and (b or c)"
    exp = boolean._parse_expression(s)
    assert str(s) == s
