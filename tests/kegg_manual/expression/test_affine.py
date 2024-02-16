# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-16 20:27:38
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 20:35:15
 * @FilePath: /KEGG/tests/kegg_manual/expression/test_affine.py
 * @Description:
"""
# """

from kegg_manual.expression.affine import V
from kegg_manual.expression.affine import Expression as E


def test_expression_parse():
    e = E.parse("2x + 3")
    assert e == E({V("x"): 2}, 3)
    assert str(e) == "2x + 3"
    assert E.parse("1") == 1
    assert E.parse("x + 0y + 0") == V("x")
    assert E.parse("- x") == -V("x")
    assert E.parse("-2x1 + 5pi - 3x2") == (-V("x1") * 2 + V("pi") * 5 - 3 * V("x2"))
    assert E.parse("-2x1 + 5pi - 3x1") == (V("pi") * 5 - 5 * V("x1"))
