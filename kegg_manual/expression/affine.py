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


import numbers
import re

from .. import utils


class V(utils.Variable):
    """Represents a variable in an expression

    Equality of variables is based on the symbol.
    """

    @property
    def _MultiVars(self):
        return Expression

    def __eq__(self, other):
        """Check equality of variables"""
        if isinstance(other, self._MultiVars):
            return other == self
        return isinstance(other, self.__class__) and self._symbol == other._symbol

    def __hash__(self):
        return super().__hash__()


class Expression(utils.LineExpression):
    """Represents an affine expression (e.g. 2x + 3y - z + 5)"""

    def __init__(self, arg: dict[V, int] | None = None, /, _vars=None):
        """Create new expression

        >>> Expression({ Variable('x'): 2 }, 3)
        Expression('2x + 3')
        >>> Expression({ Variable('x'): 1, Variable('y'): 1 })
        Expression('x + y')
        """
        if isinstance(arg, dict):
            self._variables = {}
            self._offset = _vars if _vars is not None else 0

            variables = arg or {}
            for var, value in variables.items():
                if not isinstance(var, V):
                    raise ValueError("Not a variable: {}".format(var))
                if value != 0:
                    self._variables[var] = value

    def __mul__(self, other):
        """Multiply by scalar"""
        if isinstance(other, numbers.Real):
            return super().__mul__(other)
        return NotImplemented

    @classmethod
    def parse(cls, s):
        return cls(*_parse_string(s))


def _parse_string(s: str):
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
            _variables[V(variable, symbol_strict=True)] = (
                _variables.get(V(variable, symbol_strict=True), 0) + state_number
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


if __name__ == "__main__":
    import doctest

    doctest.testmod()
