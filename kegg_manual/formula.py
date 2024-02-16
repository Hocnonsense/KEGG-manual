# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-15 21:53:25
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 20:59:20
 * @FilePath: /KEGG/kegg_manual/formula.py
 * @Description:
 Parser and representation of chemical formulas.


Chemical formulas (:class:`.Formula`) are represented as a number of
:class:`FormulaElements <.FormulaElement>` with associated counts. A
:class:`.Formula` is itself a :class:`.FormulaElement` so a formula can contain
subformulas. This allows some simple structure to be represented.

 * @OriginalLicense:

This file is part of PSAMM.

PSAMM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PSAMM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PSAMM.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2014-2017  Jon Lund Steffensen <jon_steffensen@uri.edu>
Copyright 2015-2020  Keith Dufault-Thompson <keitht547@my.uri.edu>
"""

import re
from collections import Counter
import functools
import operator
import numbers
from typing import TYPE_CHECKING

from .utils import ParseError, Variable, LineExpression


class FormulaElement(Variable):
    """Base class representing elements of a formula"""

    @property
    def _MultiVars(self):
        return Formula

    def __add__(self, other):
        """Add formula elements creating subformulas"""
        if isinstance(other, FormulaElement):
            if self == other:
                return self._MultiVars({self: 2})
            return self._MultiVars({self: 1, other: 1})
        return NotImplemented

    def __mul__(self, other):
        """Multiply formula element by other"""
        return self._MultiVars({self: other})

    def __eq__(self, other):
        return isinstance(other, FormulaElement) and self._symbol == other._symbol

    def substitute(self, mapping):
        """Return formula element with substitutions performed"""
        return self


class _AtomType(type):
    """Metaclass that gives the Atom class properties for each element.

    A class based on this metaclass (i.e. :class:`.Atom`) will have singleton
    elements with each name, and will have a property for each element which
    contains the instance for that element.
    """

    _ELEMENTS = set(
        "H                                                  He "
        "Li Be                               B  C  N  O  F  Ne "
        "Na Mg                               Al Si P  S  Cl Ar "
        "K  Ca Sc Ti V  Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
        "Rb Sr Y  Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I  Xe "
        "Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu "
        "         Hf Ta W  Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
        "Fr Ra Ac Th Pa U  Np Pu Am Cm Bk Cf Es Fm Md No Lr "
        "         Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
        "                                    Uut   Uup  Uus Uuo".split()
    )

    _instances: dict["_AtomType", dict] = {}

    def __call__(self, name, *args, **kwargs):
        instances = _AtomType._instances.setdefault(self, {})
        if name not in instances:
            instances[name] = super(_AtomType, self).__call__(name, *args, **kwargs)
        return instances[name]

    def __getattribute__(self, name):
        if name in _AtomType._ELEMENTS:
            return self(name)
        return super(_AtomType, self).__getattribute__(name)


@functools.total_ordering
class Atom(FormulaElement, metaclass=_AtomType):
    """Represent an atom in a chemical formula

    >>> hydrogen = Atom.H
    >>> oxygen = Atom.O
    >>> str(oxygen | 2*hydrogen)
    'H2O'
    >>> Atom.H.symbol
    'H'
    """

    def __hash__(self):
        return hash("Atom") ^ hash(self._symbol)

    def __eq__(self, other):
        return isinstance(other, Atom) and self._symbol == other._symbol

    def __lt__(self, other):
        if isinstance(other, Atom):
            return self._symbol < other._symbol
        return NotImplemented

    if TYPE_CHECKING:
        H: "Atom" = None  # type: ignore [assignment]
        He = Li = Be = B = C = N = O = F = Ne = Na = Mg = Al = Si = P = S = Cl = Ar = (
            K
        ) = Ca = Sc = Ti = V = Cr = Mn = Fe = Co = Ni = Cu = Zn = Ga = Ge = As = Se = (
            Br
        ) = Kr = Rb = Sr = Y = Zr = Nb = Mo = Tc = Ru = Rh = Pd = Ag = Cd = In = Sn = (
            Sb
        ) = Te = I = Xe = Cs = Ba = La = Ce = Pr = Nd = Pm = Sm = Eu = Gd = Tb = Dy = (
            Ho
        ) = Er = Tm = Yb = Lu = Hf = Ta = W = Re = Os = Ir = Pt = Au = Hg = Tl = Pb = (
            Bi
        ) = Po = At = Rn = Fr = Ra = Ac = Th = Pa = U = Np = Pu = Am = Cm = Bk = Cf = (
            Es
        ) = Fm = Md = No = Lr = Rf = Db = Sg = Bh = Hs = Mt = Ds = Rg = Cn = Nh = Fl = (
            Mc
        ) = Lv = Ts = Og = Uut = Uup = Uus = Uuo = H


class Radical(FormulaElement):
    """
    Represents a radical or other unknown subformula

    >>> Radical('R1').symbol
    'R1'
    """

    def __hash__(self):
        return hash("Radical") ^ hash(self._symbol)

    def __eq__(self, other):
        return isinstance(other, Radical) and self._symbol == other._symbol


class Formula(LineExpression):
    """Representation of a chemial formula

    This is represented as a number of
    :class:`FormulaElements <.FormulaElement>` with associated counts.

    >>> f = Formula({Atom.C: 6, Atom.H: 12, Atom.O: 6})
    >>> str(f)
    'C6H12O6'
    """

    def __init__(self, values: dict[FormulaElement, int | LineExpression] = {}):
        self._not_yet_fix: set[Variable] = set()
        self._variables: Counter[FormulaElement] = Counter()  # type: ignore [assignment]

        for element, value in values.items():
            if not isinstance(element, FormulaElement):
                raise ValueError("Not a formula element: {}".format(repr(element)))
            if value != 0 and (not isinstance(element, Formula) or len(element) > 0):
                self._variables[element] = value  # type: ignore [assignment]

            if isinstance(value, LineExpression):
                for var in value.variables():
                    self._not_yet_fix.add(var)
            if isinstance(element, Formula):
                for var in element.variables():
                    self._not_yet_fix.add(var)

    def substitute(self, mapping):
        result = self.__class__()
        for element, value in self._variables.items():
            if callable(getattr(value, "substitute", None)):
                value_ = getattr(value, "substitute")(mapping)
                if isinstance(value_, int) and value_ <= 0:
                    raise ValueError("Expression evaluated to non-positive number")
            # TODO does not merge correctly with subformulas
            result += value_ * element.substitute(mapping)
        return result

    def simplify(self):
        """Return formula where subformulas have been flattened

        >>> str(Formula.parse('(CH2)(CH2)2').flattened())
        'C3H6'
        """

        stack: list[tuple[FormulaElement | Formula, int]] = [(self, 1)]
        result: dict = Counter()
        while len(stack) > 0:
            var, value = stack.pop()
            if isinstance(var, Formula):
                for sub_var, sub_value in var._variables.items():
                    stack.append((sub_var, value * sub_value))
            else:
                result[var] += value
        return Formula(result)

    def is_variable(self):
        return len(self._not_yet_fix) > 0

    def __str__(self):
        """Return formula represented using Hill notation system

        >>> str(Formula({Atom.C: 6, Atom.H: 12, Atom.O: 6}))
        'C6H12O6'
        """

        def hill_sorted_elements(values):
            def element_sort_key(pair):
                element, value = pair
                if isinstance(element, Atom):
                    return 0, element.symbol
                elif isinstance(element, Radical):
                    return 1, element.symbol
                else:
                    return 2, None

            if Atom.C in values:
                yield Atom.C, values[Atom.C]
                if Atom.H in values:
                    yield Atom.H, values[Atom.H]
                for element, value in sorted(values.items(), key=element_sort_key):
                    if element not in (Atom.C, Atom.H):
                        yield element, value
            else:
                for element, value in sorted(values.items(), key=element_sort_key):
                    yield element, value

        s = ""
        for element, value in hill_sorted_elements(self._variables):

            def grouped(element, value):
                return "({}){}".format(element, value if value != 1 else "")

            def nongrouped(element, value):
                return "{}{}".format(element, value if value != 1 else "")

            if isinstance(element, Radical):
                if len(element.symbol) == 1:
                    s += nongrouped(element, value)
                else:
                    s += grouped(element, value)
            elif isinstance(element, Atom):
                s += nongrouped(element, value)
            else:
                s += grouped(element, value)
        return s

    def __and__(self, other):
        """Intersection of formula elements."""
        if isinstance(other, Formula):
            return Formula(dict(self._variables & other._variables))
        elif isinstance(other, FormulaElement):
            return Formula(dict(self._variables & Counter([other])))
        return NotImplemented

    def __or__(self, other):
        """Merge formulas into one formula."""
        # Note: This operator corresponds to the add-operator on Counter not
        # the or-operator! The add-operator is used here (on the superclass)
        # to compose formula elements into subformulas.
        if isinstance(other, Formula):
            return Formula(dict(self._variables | other._variables))
        elif isinstance(other, FormulaElement):
            return Formula(dict(self._variables | Counter([other])))
        return NotImplemented

    def __sub__(self, other):
        """Substract other formula from this formula."""
        if isinstance(other, Formula):
            return Formula(dict(self._variables - other._variables))
        elif isinstance(other, FormulaElement):
            return Formula(dict(self._variables - Counter([other])))
        return NotImplemented

    def __mul__(self, other):
        """Multiply formula element by other."""
        values = {key: value * other for key, value in self._variables.items()}
        return Formula(values)

    def __eq__(self, other):
        return isinstance(other, Formula) and self._variables == other._variables

    @classmethod
    def parse(cls, s):
        """
        Parse a formula string (e.g. C6H10O2).

        >>> from kegg_manual import formula
        >>> form = formula.Formula.parse(str("C6H10O2"))
        >>> form = formula.Formula.parse(str("C20H28N6O13PR(C5H8O6PR)n"))
        """
        return cls(_parse_formula(s))

    @classmethod
    def balance(cls, lhs, rhs):
        """Return formulas that need to be added to balance given formulas

        Given complete formulas for right side and left side of a reaction,
        calculate formulas for the missing compounds on both sides. Return
        as a left, right tuple. Formulas can be flattened before balancing
        to disregard grouping structure.
        """

        def missing(formula, other):
            for element, value in formula._values.items():
                if element not in other._values:
                    yield value * element
                else:
                    delta = value - other._values[element]
                    if isinstance(delta, numbers.Number) and delta > 0:  # type: ignore [operator]
                        yield delta * element

        return (
            functools.reduce(operator.or_, missing(rhs, lhs), Formula()),
            functools.reduce(operator.or_, missing(lhs, rhs), Formula()),
        )


def _parse_formula(s: str):
    """Parse formula string."""
    scanner = re.compile(
        r"""
        (\s+) |         # whitespace
        (\(|\)) |       # group
        ([A-Z][a-z]*) | # element
        (\d+) |         # number
        ([a-z]) |       # variable
        (\Z) |          # end
        (.)             # error
        """,
        re.DOTALL | re.VERBOSE,
    )

    def transform_subformula(form):
        """Extract radical if subformula is a singleton with a radical."""
        if isinstance(form, dict) and len(form) == 1:
            # A radical in a singleton subformula is interpreted as a
            # numbered radical.
            element, value = next(iter(form.items()))
            if isinstance(element, Radical):
                return Radical("{}{}".format(element.symbol, value))
        return form

    stack: list[dict[Atom, int] | FormulaElement] = []
    formula: dict[Atom, int] | FormulaElement = {}
    expect_count = False

    def close(formula, count=1):
        if len(stack) == 0:
            raise ParseError("Unbalanced parenthesis group in formula")
        subformula = transform_subformula(formula)
        if isinstance(subformula, dict):
            subformula = Formula(subformula)

        formula = stack.pop()
        formula[subformula] = formula.get(subformula, 0) + count
        return formula

    a = re.finditer(scanner, s)
    for match in re.finditer(scanner, s):
        match = next(a)
        (whitespace, group, element, number, variable, end, error) = match.groups()
        print(
            f"{whitespace = }\n"
            f"{group = }\n"
            f"{element = }\n"
            f"{number = }\n"
            f"{variable = }\n"
            f"{end = }\n"
            f"{error = }\n"
        )
        print(f"{stack = }\n" f"{formula = }\n" f"{expect_count = }\n")

        if error is not None:
            raise ParseError(
                "Invalid token in formula string: {!r}".format(match.group(0)),
                span=(match.start(), match.end()),
            )
        if whitespace is not None:
            continue
        if group is not None and group == "(":
            if expect_count:
                formula = close(formula)
            stack.append(formula)
            formula = {}
            expect_count = False
        elif group is not None and group == ")":
            if expect_count:
                formula = close(formula)
            expect_count = True
        elif element is not None:
            if expect_count:
                formula = close(formula)
            stack.append(formula)
            if element in "RX":
                formula = Radical(element)
            else:
                formula = Atom(element)
            expect_count = True
        elif number is not None and expect_count:
            formula = close(formula, int(number))
            expect_count = False
        elif variable is not None and expect_count:
            formula = close(formula, Variable(variable))
            expect_count = False
        elif end is not None:
            if expect_count:
                formula = close(formula)
        else:
            raise ParseError(
                "Invalid token in formula string: {!r}".format(match.group(0)),
                span=(match.start(), match.end()),
            )

    if len(stack) > 0:
        raise ParseError("Unbalanced parenthesis group in formula")

    assert isinstance(formula, dict)
    return formula
