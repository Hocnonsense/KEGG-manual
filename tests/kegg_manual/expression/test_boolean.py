# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-16 00:03:38
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 17:55:28
 * @FilePath: /KEGG/tests/kegg_manual/expression/test_boolean.py
 * @Description:
"""
# """


from kegg_manual import utils
from kegg_manual.expression.boolean import (
    SubstitutionError,
    And,
    Or,
    Expression,
    _parse_expression,
)

from kegg_manual.utils import Variable as V

# from kegg_manual.expression.affine import Variable


def test_operator_len():
    assert len(And(V("b1"), V("b2"))) == 2
    assert len(Or(V("b1"), And(V("b2"), V("b3")))) == 2


def test_expression():
    s = "a and (b or c)"
    e = Expression(s)
    e._root
    assert str(e.root) == s
    assert str(e) == s


def test_expression_substitute_one():
    e = Expression("b1")
    e1 = e.substitute(lambda v: {"b1": True}.get(v.symbol, v))
    assert e1.value is True, "existing"
    e1 = e.substitute(lambda v: {"b1": False}.get(v.symbol, v))
    assert e1.value is False, "existing_false"
    e1 = e.substitute(lambda v: v)
    assert e1 == Expression(V("b1")), "unknown_to_variable"


def test_expression_substitute_and():
    e = Expression("b1 and b2")
    e1 = e.substitute(lambda v: v)
    assert e1 == e, "unknown_to_expression"
    try:
        e.substitute(lambda v: {"b1": 17}.get(v.symbol, v))  # type: ignore [return-value, arg-type]
    except SubstitutionError:
        pass
    else:
        assert False, "invalid"
    e1 = e.substitute(lambda v: {"b1": True}.get(v.symbol, v))
    assert e1 == Expression(V("b2")), "remove_terms_from_and"
    e1 = e.substitute(lambda v: True)
    assert e1 == Expression(True), "evaluate_all_and_terms_to_true(self):"


def test_expression_substitute_or():
    e = Expression("a or b")
    # "remove_terms_from_or"
    e1 = e.substitute(lambda v: {"a": False}.get(v.symbol, v))
    assert e1 == Expression(V("b"))
    # "evaluate_all_or_terms_to_false"
    e1 = e.substitute(lambda v: False)
    assert e1 == Expression(False)


def test_expression_substitute_circuit():
    e = Expression("a and (b or c) and d")
    e1 = e.substitute(lambda v: {"a": False}.get(v.symbol, v))
    assert e1.value is False, "with_short_circuit_and"

    e = Expression("(a and b) or c or d")
    e1 = e.substitute(lambda v: {"c": True}.get(v.symbol, v))
    assert e1.value is True, "with_short_circuit_or"


def test_expression_parse():
    e = Expression("b1 and b2")
    assert e == Expression(And(V("b1"), V("b2"))), "and"
    assert e == Expression("(b1 and b2 )"), "parenthesis_with_space_right"
    assert e == Expression("( b1 and b2)"), "parenthesis_with_space_left"

    e = Expression("b1 or b2")
    assert e == Expression(Or(V("b1"), V("b2"))), "or"
    assert Expression("andor and orand") == Expression(
        And(V("andor"), V("orand"))
    ), "name_with_or_and"
    assert Expression("b1    and   b2       and b3") == Expression(
        And(V("b1"), V("b2"), V("b3"))
    ), "with_extra_space"


def test_expression_iter_variables():
    e = Expression(Or(And(V("b1"), V("b2")), And(V("b3"), V("b4"))))
    assert list(e.variables) == [V("b1"), V("b2"), V("b3"), V("b4")]


def test_expression_root():
    assert isinstance(Expression(Or(V("b1"), V("b2"))).root, Or)
    assert Expression(False).root is False, "boolean"


def test_expression_string():
    for s in ("(a and b) or (c and d)", V("a"), False):
        assert str(Expression(s)) == str(s)


def test_expression_parse_multiple():
    assert Expression("b1 and b2 and b1 and b4") == Expression(
        And(V("b1"), V("b2"), V("b4"))
    ), "with_duplicates"

    e = Expression(And(V("b1"), V("b2"), V("b3"), V("b4")))
    assert e == Expression("b1 and b2 and b3 and b4"), "_and"
    assert e == Expression("b1 and (b2 and b3) and b4"), "parenthesis_and"

    e = Expression(Or(V("b1"), V("b2"), V("b3"), V("b4")))
    assert e == Expression("b1 or b2 or b3 or b4"), "or"
    assert e == Expression("b1 or (b2 or b3) or b4"), "parenthesis_or"

    e = Expression("(b1 and b2) or (b3 and b4)")
    assert e == Expression(
        Or(And(V("b1"), V("b2")), And(V("b3"), V("b4")))
    ), "parentheses_mixed_1"
    assert e == Expression("b1 and b2 or b3 and b4"), "implicit_mixed_1"

    assert Expression("(b1 or b2) and (b3 or b4)") == Expression(
        And(Or(V("b1"), V("b2")), Or(V("b3"), V("b4")))
    ), "parentheses_mixed_2"

    assert Expression("b1 or b2 and b3 or b4") == Expression(
        Or(V("b1"), And(V("b2"), V("b3")), V("b4"))
    ), "implicit_mixed_2"

    assert Expression("(b1 AND b2) OR b3") == Expression(
        Or(V("b3"), And(V("b1"), V("b2")))
    ), "uppercase_operators"

    assert Expression("(b1 or (b2 and (b3 or (b4 and (b5)))))") == Expression(
        Or(V("b1"), And(V("b2"), Or(V("b3"), And(V("b4"), V("b5")))))
    ), "parentheses_right_nested"
    assert Expression("(((b1 or b2) and b3) or b4) and (b5)") == Expression(
        And(V("b5"), Or(V("b4"), And(V("b3"), Or(V("b1"), V("b2")))))
    ), "parentheses_left_nested"

    assert Expression("b12345 and bxyz and testtesttest") == Expression(
        And(V("b12345"), V("bxyz"), V("testtesttest"))
    ), "longer_names"

    assert Expression("[(a or b) or (c or d)] or [e or (f and g and h)]") == Expression(
        Or(V("a"), V("b"), V("c"), V("d"), V("e"), And(V("f"), V("g"), V("h")))
    ), "with_square_mixed_groups"


def test_expression_parse_with_missing():
    for s in ("b1 and and b3", "b1 and (b2 or b3", "[(a or b) or (c or d])"):
        try:
            e = Expression(s)
        except utils.ParseError:
            pass
        else:
            assert False


def test__parse_expression():
    s = "a and (b or c)"
    exp = _parse_expression(s)
    assert str(s) == s
