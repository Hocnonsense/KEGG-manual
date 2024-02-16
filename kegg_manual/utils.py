# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 21:22:22
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 11:58:37
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
import collections.abc
import functools
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

    def __init__(self, symbol, strict=False):
        """Create variable with given symbol

        in strict mode, Symbol must
        - start with a letter or underscore
        - but can contain numbers in other positions
        - other characters now allowed

        >>> Variable('x')
        Variable('x')
        >>> # Variable('123'), Variable('x.1'), Variable('')
        """
        if strict and not re.match(r"^[^\d\W]\w*\Z", symbol):
            raise ValueError("Invalid symbol `{}`".format(symbol))
        self._symbol = str(symbol)

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
        return str("Variable({})").format(repr(self._symbol))

    def __str__(self):
        return self._symbol

    def __eq__(self, other):
        return isinstance(other, Variable) and self._symbol == other._symbol

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash("Variable") ^ hash(self._symbol)

    def __lt__(self, other):
        if isinstance(other, Variable):
            return self._symbol < other._symbol
        return NotImplemented
