# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 21:22:22
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 20:45:34
 * @FilePath: /KEGG/kegg_manual/utils.py
 * @Description:
    Utilities for keeping track of parsing context.
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

Copyright 2015  Jon Lund Steffensen <jon_steffensen@uri.edu>
Copyright 2015-2020  Keith Dufault-Thompson <keitht547@my.uri.edu>
"""
# """

import abc
from collections import Counter
import collections.abc
import functools
import numbers
import re
from pathlib import Path
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


class ParseError(Exception):
    """Exception used to signal errors while parsing"""

    def __init__(self, *args, **kwargs):
        self._span = kwargs.pop("span", None)
        super(ParseError, self).__init__(*args, **kwargs)

    @property
    def indicator(self):
        if self._span is None:
            return None
        pre = " " * self._span[0]
        ind = "^" * max(1, self._span[1] - self._span[0])
        return pre + ind


class FileMark:
    """Marks a position in a file.

    This is used when parsing input files, to keep track of the position that
    generates an entry.
    """

    def __init__(self, filecontext, line: int, column: int):
        self._filecontext = filecontext
        self._line = line
        self._column = column

    @property
    def filecontext(self):
        return self._filecontext

    @property
    def line(self):
        return self._line

    @property
    def column(self):
        return self._column

    def __str__(self):
        result = str(self._filecontext)
        if self._line is not None:
            result += ":{}".format(self._line)
            if self._column is not None:
                result += ":{}".format(self._column)
        return result

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"({repr(self._filecontext)}, "
            f" {repr(self._line)}, "
            f" {repr(self._column)})"
        )


class ModelEntry(metaclass=abc.ABCMeta):
    """Abstract model entry.

    Provdides a base class for model entries which are representations of any entity (such as compound, reaction or compartment) in a model.
    An entity has an ID, and may have a name and filemark.

    The ID is a unique string identified within a model.
    The name is a string identifier for human consumption.
    The filemark indicates where the entry originates from e.g. file name and line number).

    Any additional properties for an entity exist in ``properties`` which is any dict-like object mapping from string keys to any value type. The ``name`` entry in the dictionary corresponds to the name. Entries can be mutable, where the properties can be modified, or immutable, where the properties cannot be modified or where modifications are ignored. The ID is always immutable.
    """

    @abc.abstractproperty
    def id(self):
        """Identifier of entry."""

    @property
    def name(self) -> str | None:
        """Name of entry (or None)."""
        name = self.properties.get("name")
        if not name:
            return None
        assert isinstance(name[0], str)
        return name[0]

    @abc.abstractproperty
    def properties(self) -> dict[str, list[str | tuple[str, list[str]]]]:
        """Properties of entry as a :class:`Mapping` subclass (e.g. dict).

        Note that the properties are not generally mutable but may be mutable
        for specific subclasses. If the ``id`` exists in this dictionary, it
        must never change the actual entry ID as obtained from the ``id``
        property, even if other properties are mutable.
        """

    @abc.abstractproperty
    def filemark(self):
        """Position of entry in the source file (or None)."""

    def __repr__(self):
        return str("<{} id={!r}>").format(self.__class__.__name__, self.id)


class RheaDb:
    """Allows storing and searching Rhea db"""

    def __init__(self, filepath: str | Path):
        self._values = self._parse_db_from_tsv(filepath)

    @staticmethod
    def _parse_db_from_tsv(filepath: str | Path):
        """
        $ head psamm/external-data/chebi_pH7_3_mapping.tsv
        CHEBI   CHEBI_PH7_3     ORIGIN
        3       3       computation
        7       7       computation
        8       8       computation
        19      19      computation
        20      20      computation
        """
        db: dict[str, str] = {}
        with open(filepath) as f:
            for line in f:
                split = line.split("\t")
                db[split[0]] = split[1]
        return db

    def select_chebi_id(self, id_list: list[str]):
        return [self._values[x] for x in id_list if x in self._values]


class FozenDict(collections.abc.Mapping):
    """An immutable wrapper around another dict-like object."""

    def __init__(self, d: dict):
        self.__d = d

    def __getitem__(self, key):
        return self.__d[key]

    def __iter__(self):
        return iter(self.__d)

    def __len__(self):
        return len(self.__d)

    def __eq__(self, __other: object) -> bool:
        return self.__d.__eq__(__other)

    def __str__(self) -> str:
        return self.__d.__str__()

    def __repr__(self) -> str:
        return self.__d.__repr__()


class FrozenOrderedSet(collections.abc.Set, collections.abc.Hashable):
    """An immutable set that retains insertion order."""

    def __init__(self, seq: Iterable | None = None):
        self.__d: dict = collections.OrderedDict()
        for e in seq or []:
            self.__d[e] = None

    def __contains__(self, element):
        return element in self.__d

    def __iter__(self):
        return iter(self.__d)

    def __len__(self):
        return len(self.__d)

    def __hash__(self):
        h = 0
        for e in self:
            h ^= 31 * hash(e)
        return h

    def __repr__(self):
        return str("{}({})").format(self.__class__.__name__, list(self))


@functools.total_ordering
class Variable:
    """Represents a variable in an expression

    Equality of variables is based on the symbol.
    """

    def __init__(self, symbol, symbol_strict=False):
        """Create variable with given symbol

        in strict mode, Symbol must
        - start with a letter or underscore
        - but can contain numbers in other positions
        - other characters now allowed

        >>> Variable('x')
        Variable('x')
        >>> # Variable('123'), Variable('x.1'), Variable('')
        """
        if isinstance(symbol, Variable):
            symbol = symbol._symbol  # type: ignore [has-type]
        if symbol_strict and not re.match(r"^[^\d\W]\w*\Z", symbol):
            raise ValueError("Invalid symbol `{}`".format(symbol))
        self._symbol = symbol

    @property
    def symbol(self):
        """Symbol of variable

        >>> Variable('x').symbol
        'x'
        """
        return self._symbol

    def simplify(self):
        """Return simplified expression

        The simplified form of a variable is always the
        variable itself.

        >>> Variable('x').simplify()
        Variable('x')
        """
        return self

    def substitute(self, mapping: Callable[["Variable"], T]) -> T:
        """Return expression with variables substituted

        >>> Variable('x').substitute(lambda v: {'x': 567}.get(v.symbol, v))
        567
        >>> Variable('x').substitute(lambda v: {'y': 42}.get(v.symbol, v))
        Variable('x')
        >>> Variable('x').substitute(
        ...     lambda v: {'x': 123, 'y': 56}.get(v.symbol, v))
        123
        """

        return mapping(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self._symbol)})"

    def __str__(self):
        return f"{self._symbol}"

    def __eq__(self, other):
        """Check equality of variables"""
        if isinstance(self._symbol, numbers.Real):
            return other == self._symbol
        if isinstance(other, self._MultiVars):
            return other == self
        return isinstance(other, self.__class__) and self._symbol == other._symbol

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash("Variable") ^ hash(self._symbol)

    def __lt__(self, other):
        if isinstance(other, Variable):
            return self._symbol < other._symbol
        return NotImplemented

    @property
    def _MultiVars(self):
        return LineExpression

    def __neg__(self):
        return self * -1

    def __add__(self, other):
        if isinstance(self._symbol, numbers.Real):
            return self.__class__(self._symbol + other)
        return self._MultiVars({self: 1}) + other

    def __mul__(self, other):
        if isinstance(self._symbol, numbers.Real):
            return self.__class__(self._symbol * other)
        return self._MultiVars({self: 1}) * other

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self._MultiVars({self: 1}) - other

    def __rsub__(self, other):
        return -self + other

    def __or__(self, other):
        """Merge formula elements into one formula"""
        if isinstance(self._symbol, numbers.Real):
            return self.__class__(self._symbol | other)
        return self._MultiVars({self: 1}) | other

    def __ror__(self, other):
        return self | other

    def __rmul__(self, other):
        return self * other

    def repeat(self, count):
        """Repeat formula element by creating a subformula"""
        return self * count

    def __div__(self, other):
        if isinstance(self._symbol, numbers.Real):
            return self.__class__(self._symbol / other)
        return self._MultiVars({self: 1}) / other

    __truediv__ = __div__

    def __floordiv__(self, other):
        if isinstance(self._symbol, numbers.Real):
            return self.__class__(self._symbol // other)
        return self._MultiVars({self: 1}) // other


class LineExpression(Variable):
    """Represents an affine expression (e.g. 2x + 3y - z + 5)"""

    def __init__(self, arg: dict[Variable, int] | None = None, /, _vars=0):
        """Create new expression

        >>> Expression({ Variable('x'): 2 }, 3)
        Expression('2x + 3')
        >>> Expression({ Variable('x'): 1, Variable('y'): 1 })
        Expression('x + y')
        """
        self._variables: dict[Variable, int] = {}
        self._offset = _vars

        variables = arg or {}
        for var, value in variables.items():
            if not isinstance(var, Variable):
                raise ValueError("Not a variable: {}".format(var))
            if value != 0:
                self._variables[var] = value

    @classmethod
    def parse(cls, s: str):
        return Variable(s)

    @property
    def _symbol(self):
        return str(self)

    def variables(self):
        """Return iterator of variables in expression"""
        yield from self._variables

    def simplify(self):
        """Return simplified expression.

        If the expression is of the form 'x', the variable will be returned,
        and if the expression contains no variables, the offset will be
        returned as a number.
        """
        if len(self._variables) == 0:
            return self._offset
        if len(self._variables) == 1 and self._offset == 0:
            for var, value in self._variables.items():
                if value == 1:
                    return var.simplify()
        result = self.__class__({}, self._offset)
        for var, value in self._variables.items():
            result += var.simplify() * value
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

    def __iter__(self):
        yield from self._variables

    def items(self):
        """Iterate over (:class:`.FormulaElement`, value)-pairs"""
        return self._variables.items()

    def __contains__(self, element):
        return element in self._variables

    def get(self, element, default=None):
        """Return value for element or default if not in the formula."""
        return self._variables.get(element, default)

    def __getitem__(self, element):
        if element not in self._variables:
            raise KeyError(repr(element))
        return self._variables[element]

    def __len__(self):
        return len(self._variables)

    def __add__(self, other):
        """Add expressions, variables or numbers"""
        if isinstance(other, numbers.Number):
            return self.__class__(self._variables, self._offset + other)
        if isinstance(other, LineExpression):
            _variables = Counter(self._variables)
            _variables.update(other._variables)
            variables = {var: value for var, value in _variables.items() if value != 0}
            return self.__class__(variables, self._offset + other._offset)
        if isinstance(other, Variable):
            return self + LineExpression({other: 1})
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
        return self.__class__(
            {var: value * other for var, value in self._variables.items()},
            self._offset * other,
        )

    def __rmul__(self, other):
        return self * other

    def __div__(self, other):
        """Divide by scalar"""
        if isinstance(other, numbers.Real):
            return self.__class__(
                {var: value / other for var, value in self._variables.items()},
                self._offset / other,
            )
        return NotImplemented

    __truediv__ = __div__

    def __floordiv__(self, other):
        if isinstance(other, numbers.Real):
            return self.__class__(
                {var: value // other for var, value in self._variables.items()},
                self._offset // other,
            )
        return NotImplemented

    def __neg__(self):
        return self * -1

    def __eq__(self, other):
        """Expression equality"""
        if isinstance(other, LineExpression):
            return self._variables == other._variables and self._offset == other._offset
        elif isinstance(other, Variable):
            # Check that there is just one variable in the expression
            # with a coefficient of one.
            return (
                self._offset == 0
                and len(self._variables) == 1
                and list(self._variables.keys())[0] == other
                and list(self._variables.values())[0] == 1
            )
        elif isinstance(other, numbers.Number):
            return len(self._variables) == 0 and self._offset == other
        return False

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"

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
        for i, (symbol, value) in enumerate(all_terms()):
            if i == 0:
                # First term is special
                if symbol is None:
                    terms.append(f"{value}")
                elif abs(value) == 1:
                    terms.append(symbol if value > 0 else "-" + symbol)
                else:
                    terms.append(f"{value}{symbol}")
            else:
                prefix = "+" if value >= 0 else "-"
                if symbol is None:
                    terms.append(f"{prefix} {abs(value)}")
                elif abs(value) == 1:
                    terms.append(f"{prefix} {symbol}")
                else:
                    terms.append(f"{prefix} {abs(value)}{symbol}")
        return " ".join(terms)

    def __hash__(self):
        h = hash(self.__class__.__name__)
        for element, value in self._variables.items():
            h ^= hash(element) ^ hash(value)
        return h
