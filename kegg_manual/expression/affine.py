# This file is part of PSAMM.
#
# PSAMM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PSAMM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PSAMM.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2015  Jon Lund Steffensen <jon_steffensen@uri.edu>
# Copyright 2015-2020  Keith Dufault-Thompson <keitht547@my.uri.edu>

"""Representations of affine expressions and variables.

These classes can be used to represent affine expressions
and do manipulation and evaluation with substitutions of
particular variables.
"""


import re
import numbers
from collections import Counter

from .. import utils


class V(utils.Variable):
    """Represents a variable in an expression

    Equality of variables is based on the symbol.
    """

    def __add__(self, other):
        return Expression({self: 1}) + other

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return Expression({self: 1}) - other

    def __rsub__(self, other):
        return -self + other

    def __mul__(self, other):
        return Expression({self: 1}) * other

    def __rmul__(self, other):
        return self * other

    def __div__(self, other):
        return Expression({self: 1}) / other

    __truediv__ = __div__

    def __floordiv__(self, other):
        return Expression({self: 1}) // other

    def __neg__(self):
        return Expression({self: -1})

    def __eq__(self, other):
        """Check equality of variables"""
        if isinstance(other, Expression):
            return other == self
        return isinstance(other, V) and self._symbol == other._symbol

    def __hash__(self):
        return hash("Variable") ^ hash(self._symbol)


class Expression:
    """Represents an affine expression (e.g. 2x + 3y - z + 5)"""

    def __init__(self, arg=None, /, _vars=None):
        """Create new expression

        >>> Expression({ Variable('x'): 2 }, 3)
        Expression('2x + 3')
        >>> Expression({ Variable('x'): 1, Variable('y'): 1 })
        Expression('x + y')
        """

        if _vars is None and isinstance(arg, str):
            # Parse as string
            self._variables, self._offset = self._parse_string(arg)
        else:
            self._variables = {}
            self._offset = arg if _vars is not None else 0

            variables = arg or {}
            for var, value in variables.items():
                if not isinstance(var, V):
                    raise ValueError("Not a variable: {}".format(var))
                if value != 0:
                    self._variables[var] = value

    def _parse_string(self, s):
        """Parse expression string

        Variables must be valid variable symbols and
        coefficients must be integers.
        """
        scanner = re.compile(
            r"""
            (\s+) |         # whitespace
            ([^\d\W]\w*) |  # variable
            (\d+) |         # number
            ([+-]) |        # sign
            (\Z) |          # end
            (.)             # error
        """,
            re.DOTALL | re.VERBOSE,
        )

        _variables: dict[V, int] = {}
        offset = 0

        # Parse using four states:
        # 0: expect sign, variable, number or end (start state)
        # 1: expect sign or end
        # 2: expect variable or number
        # 3: expect sign, variable or end
        # All whitespace is ignored
        state = 0
        state_number = 1
        for match in re.finditer(scanner, s):
            whitespace, variable, number, sign, end, error = match.groups()
            if error is not None:
                raise ValueError(
                    "Invalid token in expression string: {}".format(match.group(0))
                )
            elif whitespace is not None:
                continue
            elif variable is not None and state in (0, 2, 3):
                _variables[V(variable, strict=True)] = (
                    _variables.get(V(variable, strict=True), 0) + state_number
                )
                state = 1
            elif sign is not None and state in (0, 1, 3):
                if state == 3:
                    offset += state_number
                state_number = 1 if sign == "+" else -1
                state = 2
            elif number is not None and state in (0, 2):
                state_number = state_number * int(number)
                state = 3
            elif end is not None and state in (0, 1, 3):
                if state == 3:
                    offset += state_number
            else:
                raise ValueError(
                    "Invalid token in expression string: {}".format(match.group(0))
                )

        # Remove zero-coefficient elements
        variables = {var: value for var, value in _variables.items() if value != 0}
        return variables, offset

    def simplify(self):
        """Return simplified expression.

        If the expression is of the form 'x', the variable will be returned,
        and if the expression contains no variables, the offset will be
        returned as a number.
        """
        result = self.__class__(self._variables, self._offset)
        if len(result._variables) == 0:
            return result._offset
        elif len(result._variables) == 1 and result._offset == 0:
            var, value = next(result._variables.items())
            if value == 1:
                return var
        return result

    def substitute(self, mapping):
        """Return expression with variables substituted

        >>> Expression('x + 2y').substitute(
        ...     lambda v: {'y': -3}.get(v.symbol, v))
        Expression('x - 6')
        >>> Expression('x + 2y').substitute(
        ...     lambda v: {'y': Variable('z')}.get(v.symbol, v))
        Expression('x + 2z')
        """
        expr = self.__class__()
        for var, value in self._variables.items():
            expr += value * var.substitute(mapping)
        return (expr + self._offset).simplify()

    def variables(self):
        """Return iterator of variables in expression"""
        return iter(self._variables)

    def __add__(self, other):
        """Add expressions, variables or numbers"""

        if isinstance(other, numbers.Number):
            return self.__class__(self._variables, self._offset + other)
        elif isinstance(other, V):
            return self + Expression({other: 1})
        elif isinstance(other, Expression):
            _variables = Counter(self._variables)
            _variables.update(other._variables)
            variables = {var: value for var, value in _variables.items() if value != 0}
            return self.__class__(variables, self._offset + other._offset)
        return NotImplemented

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        """Subtract expressions, variables or numbers"""
        return self + -other

    def __rsub__(self, other):
        return -self + other

    def __mul__(self, other):
        """Multiply by scalar"""
        if isinstance(other, numbers.Number):
            if other == 0:
                return self.__class__()
            return self.__class__(
                {var: value * other for var, value in self._variables.items()},
                self._offset * other,
            )
        return NotImplemented

    def __rmul__(self, other):
        return self * other

    def __div__(self, other):
        """Divide by scalar"""
        if isinstance(other, numbers.Number):
            return self.__class__(
                {var: value / other for var, value in self._variables.items()},
                self._offset / other,
            )
        return NotImplemented

    __truediv__ = __div__

    def __floordiv__(self, other):
        if isinstance(other, numbers.Number):
            return self.__class__(
                {var: value // other for var, value in self._variables.items()},
                self._offset // other,
            )
        return NotImplemented

    def __neg__(self):
        return self * -1

    def __eq__(self, other):
        """Expression equality"""
        if isinstance(other, Expression):
            return self._variables == other._variables and self._offset == other._offset
        elif isinstance(other, V):
            # Check that there is just one variable in the expression
            # with a coefficient of one.
            return (
                self._offset == 0
                and len(self._variables) == 1
                and next(self._variables.keys()) == other
                and next(self._variables.values()) == 1
            )
        elif isinstance(other, numbers.Number):
            return len(self._variables) == 0 and self._offset == other
        return False

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return f"{self.__class__.__name__}({self!r})"

    def __str__(self):
        def all_terms():
            count_vars = 0
            for symbol, value in sorted(
                (var.symbol, value) for var, value in self._variables.items()
            ):
                if value != 0:
                    count_vars += 1
                    yield symbol, value
            if self._offset != 0 or count_vars == 0:
                yield None, self._offset

        terms = []
        for i, spec in enumerate(all_terms()):
            symbol, value = spec
            if i == 0:
                # First term is special
                if symbol is None:
                    terms.append("{}".format(value))
                elif abs(value) == 1:
                    terms.append(symbol if value > 0 else "-" + symbol)
                else:
                    terms.append("{}{}".format(value, symbol))
            else:
                prefix = "+" if value >= 0 else "-"
                if symbol is None:
                    terms.append("{} {}".format(prefix, abs(value)))
                elif abs(value) == 1:
                    terms.append("{} {}".format(prefix, symbol))
                else:
                    terms.append("{} {}{}".format(prefix, abs(value), symbol))
        return " ".join(terms)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
