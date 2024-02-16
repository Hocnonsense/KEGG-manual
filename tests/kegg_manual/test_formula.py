# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-16 15:37:40
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 23:22:28
 * @FilePath: /KEGG/tests/kegg_manual/test_formula.py
 * @Description:
"""
# """

from kegg_manual import utils
from kegg_manual.formula import FormulaElement, Atom, Radical
from kegg_manual.formula import Formula as F


def test_add_formula_elements():
    e1 = FormulaElement("a")
    e2 = FormulaElement("b")
    assert e1 + e2 == F({e1: 1, e2: 1})
    assert e1 + e1 == F({e1: 2})
    assert e1 | e2 == F({e1: 1, e2: 1})
    assert e1.substitute(lambda v: {"x": 42}.get(v.symbol, v)) == e1


def test_atom():
    H = Atom("H")
    assert str(H) == "H"
    assert H.symbol == "H"
    assert Atom.H == H
    assert Atom.Zn == Atom("Zn")
    assert Atom("X").symbol == "X"
    Si = Atom.Si
    assert repr(Si) == "Atom('Si')"

    assert H != Si
    assert H < Si
    assert Atom.C < H


def test_formula_parse():
    def deparse(s: str, clean_s=""):
        f = F.parse(s)
        if clean_s:
            assert f == F.parse(clean_s)
        assert str(f) == clean_s or s, "cannot reparse to string"
        return f

    assert deparse("H2O2") == F({Atom.H: 2, Atom.O: 2}), "with_final_digit"
    assert deparse("H2O") == F({Atom.H: 2, Atom.O: 1}), "with_implicit_final_digit"
    assert deparse("OH2", "H2O") == F({Atom.H: 2, Atom.O: 1}), "equals_other_formula"
    assert deparse("ZnO") == F({Atom.Zn: 1, Atom.O: 1}), "with_wide_element"
    assert deparse("C2H5NO2") == F(
        {Atom.C: 2, Atom.H: 5, Atom.N: 1, Atom.O: 2}
    ), "with_implicit_digit"
    assert deparse("C6H10O2") == F(
        {Atom.C: 6, Atom.H: 10, Atom.O: 2}
    ), "with_wide_count"
    assert deparse("C2H6O2(CH)") == F(
        {Atom.C: 2, Atom.H: 6, Atom.O: 2, F({Atom.C: 1, Atom.H: 1}): 1}
    ), "with_implicitly_counted_subgroup"
    assert deparse("C2H6O2(CH)2") == F(
        {Atom.C: 2, Atom.H: 6, Atom.O: 2, F({Atom.C: 1, Atom.H: 1}): 2}
    ), "with_counted_subgroup"
    assert deparse("C2H6O2(CH)2(CH)2") == F(
        {Atom.C: 2, Atom.H: 6, Atom.O: 2, F({Atom.C: 1, Atom.H: 1}): 4}
    ), "with_two_identical_counted_subgroups"
    assert deparse("C2H6O2(CH)2(CH2)2") == F(
        {
            Atom.C: 2,
            Atom.H: 6,
            Atom.O: 2,
            F({Atom.C: 1, Atom.H: 1}): 2,
            F({Atom.C: 1, Atom.H: 2}): 2,
        }
    ), "with_two_identical_counted_subgroups"
    assert deparse("C2(CH)10NO2") == F(
        {Atom.C: 2, Atom.N: 1, Atom.O: 2, F({Atom.C: 1, Atom.H: 1}): 10}
    ), "with_wide_counted_subgroup"
    assert deparse("C2H4NO2R") == F(
        {Atom.C: 2, Atom.H: 4, Atom.N: 1, Atom.O: 2, Radical("R"): 1}
    ), "with_radical"
    assert deparse("C2H4NO2(R1)") == F(
        {Atom.C: 2, Atom.H: 4, Atom.N: 1, Atom.O: 2, Radical("R1"): 1}
    ), "with_numbered_radical"
    assert deparse("CH3(CH2)14(CO(OH))") == F(
        {
            Atom.C: 1,
            Atom.H: 3,
            F({Atom.C: 1, Atom.H: 2}): 14,
            F({Atom.C: 1, Atom.O: 1, F({Atom.H: 1, Atom.O: 1}): 1}): 1,
        }
    ), "to_string_with_group"

    try:
        F.parse("H2O. ABC")
    except utils.ParseError:
        pass
    else:
        assert False


def test_formula_ne():
    f = F({Atom.Au: 1})
    assert f != F({Atom.Ag: 1}), "other_with_distinct_elements"
    assert f != F({Atom.Au: 2}), "other_with_different_number"


def test_formula_multiply():
    f = F.parse("H2O")
    assert f * 0 == F(), "zero"
    assert f * 1 == f, "one"
    assert 2 * f == F.parse("H4O2"), "right_number"
    assert f * 4 == F.parse("H8O4"), "number"
    assert f * 4 == f.repeat(4), "repeat"


def test_formula_set():
    assert -F.parse("H3") == F({Atom.H: -3})
    f = F.parse("H2O")
    f1 = F.parse("NH3")
    assert f | f1 == F.parse("NH4OH"), "merge_same_formulas_with_same_atoms"
    assert F.parse("H3") | F({Atom.H: -3}) == F.parse(
        ""
    ), "merge_formulas_that_cancel_out"
    assert f & f1 == F.parse("H2"), "intersection"
    assert f1 & Atom.H == F.parse("H"), "intersection_with_atom"
    assert Atom.O & f1 == F.parse(""), "intersection_with_left_atom"
    assert f1 - f == F.parse("NH"), "subtraction"
    assert f1 == F.parse("NH4") - Atom.H, "subtraction_with_atom"


def test_formula_iter():
    f = F.parse("C6H12O6")
    assert str(f) == "C6H12O6"
    assert set(f) == {Atom.H, Atom.C, Atom.O}
    assert set(iter(f)) == {Atom.H, Atom.C, Atom.O}
    assert dict(f.items()) == {Atom.C: 6, Atom.H: 12, Atom.O: 6}
    assert Atom.C in f
    assert Atom.Ag not in f

    assert f.get(Atom.H) == 12
    assert f.get(Atom.Au) == None
    assert f.get(Atom.Hg, 4) == 4

    assert f[Atom.H] == 12
    try:
        f[Atom.Au]
    except KeyError:
        pass
    else:
        assert False

    assert len(f) == 3


def test_formula_simplify():
    f = F(
        {
            Atom.C: 1,
            Atom.H: 3,
            F({Atom.C: 1, Atom.H: 2}): 14,
            F({Atom.C: 1, Atom.O: 1, F({Atom.H: 1, Atom.O: 1}): 1}): 1,
        }
    )
    assert f.simplify() == F.parse("C16H32O2")


def test_formula_substitute():
    f = F.parse("CH3(CH2)nCOOH")
    try:
        f.substitute(lambda v: {"n": -5}.get(v.symbol, v))
    except ValueError:
        pass
    else:
        assert False, "negative"
    try:
        f.substitute(lambda v: {"n": 0}.get(v.symbol, v))
    except ValueError:
        pass
    else:
        assert False, "zero"


def test_formula_variable():
    assert not F.parse("C6H12O6").is_variable()
    assert F.parse("C2H4NO2R(C2H2NOR)n").is_variable()


def test_formula_balance():
    assert F.balance(F.parse("H2O"), F.parse("OH")) == (
        F(),
        F.parse("H"),
    ), "missing_on_one_side"
    assert F.balance(F.parse("C3H6OH"), F.parse("CH6O2")) == (
        F.parse("O"),
        F.parse("C2H"),
    ), "missing_on_both_sides"
    assert F.balance(F.parse("H2(CH2)n"), F.parse("CH3O(CH2)n")) == (
        F.parse("CHO"),
        F(),
    ), "subgroups_cancel_out"
    assert F.balance(F.parse("H2(CH2)"), F.parse("CH3O(CH2)n")) == (
        F.parse("CHO"),
        F(),
    ), "subgroups_cancel_out"
