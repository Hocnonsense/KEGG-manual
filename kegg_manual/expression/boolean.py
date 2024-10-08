# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-15 21:55:35
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 11:58:02
 * @FilePath: /KEGG/kegg_manual/expression/boolean.py
 * @Description:
 Representations of boolean expressions and variables.


These classes can be used to represent simple boolean
expressions and do evaluation with substitutions of
particular variables.

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

Copyright 2014-2015  Jon Lund Steffensen <jon_steffensen@uri.edu>
Copyright 2015-2020  Keith Dufault-Thompson <keitht547@my.uri.edu>
"""
# """

import re
from typing import Callable, Iterable, Literal, Union

from ..utils import FrozenOrderedSet, ParseError
from ..utils import Variable as V


# region _OperatorTerm
class _OperatorTerm:
    """Composite operator term."""

    def __init__(self, *args: Union[bool, V, "_OperatorTerm"]):
        terms: list[bool | V | _OperatorTerm] = []
        for arg in args:
            if isinstance(arg, self.__class__):
                terms.extend(arg)
            elif isinstance(arg, (bool, V, _OperatorTerm)):
                terms.append(arg)
            else:
                raise ValueError(f"Invalid term: {arg!r}")
        self._terms = FrozenOrderedSet(terms)

    def __iter__(self):
        return iter(self._terms)

    def __hash__(self):
        return hash(self._terms)

    def __len__(self):
        return len(self._terms)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._terms == other._terms

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return f" {self.__class__.__name__.lower()} ".join(
            (f"({i})" if isinstance(i, _OperatorTerm) else f"{i}" for i in self._terms)
        )


class And(_OperatorTerm):
    """Represents an AND term in an expression."""


class Or(_OperatorTerm):
    """Represents an OR term in an expression."""


operators = {"and": And, "or": Or, None: lambda *args: args[0]}
# endregion _OperatorTerm


class SubstitutionError(Exception):
    """Error substituting into expression."""


class Expression:
    """Boolean expression representation.

    The expression can be constructed from an expression string of
    variables, operators ("and", "or") and parenthesis groups. For example,

    >>> e = Expression('a and (b or c)')
    """

    def __init__(self, arg, _vars: Iterable | None = None):
        if isinstance(arg, (_OperatorTerm, V, bool)):
            self._root = arg
        elif isinstance(arg, str):
            self._root = _parse_expression(arg)
        else:
            raise TypeError("Unexpected arguments to Expression: {}".format(repr(arg)))

        # If present use _vars to create the set of variables directly. This
        # saves a loop over the tree nodes when the variables are already
        # known.
        if _vars is None:
            variables = []
            if isinstance(self._root, (_OperatorTerm, V)):
                stack = [self._root]
                while len(stack) > 0:
                    term = stack.pop()
                    if isinstance(term, V):
                        variables.append(term)
                    elif isinstance(term, _OperatorTerm):
                        stack.extend(reversed(list(term)))
                    else:
                        raise ValueError(
                            "Invalid node in expression tree: {!r}".format(term)
                        )

            self._variables = FrozenOrderedSet(variables)
        else:
            self._variables = FrozenOrderedSet(_vars)

    @property
    def root(self):
        """Return root term, variable or boolean of the expression."""
        return self._root

    @property
    def variables(self):
        """Immutable set of variables in the expression."""
        return self._variables

    def has_value(self):
        """Return True if the expression has no variables."""
        return isinstance(self._root, bool)

    @property
    def value(self):
        """The value of the expression if fully evaluated."""
        if not self.has_value():
            raise ValueError("Expression is not fully evaluated")
        return self._root

    def substitute(
        self, mapping: Callable[["V"], _OperatorTerm | V | bool]
    ) -> "Expression":
        """Substitute variables using mapping function."""
        next_terms = iter([self._root])
        output_stack = []
        current_type = None
        variables = []
        terms: list[_OperatorTerm | V | bool | str] = []
        term: _OperatorTerm | V | bool | str | None = None

        while True:
            try:
                term = next(next_terms)
            except StopIteration:
                term = None

            if term is None:
                if current_type is None:
                    term = terms[0]
                    break
                else:
                    if len(terms) == 0:
                        if current_type == And:
                            term = True
                        elif current_type == Or:
                            term = False
                    elif len(terms) == 1:
                        term = terms[0]
                    else:
                        term = current_type(*terms)
                current_type, next_terms, terms = output_stack.pop()
            else:
                if isinstance(term, _OperatorTerm):
                    output_stack.append((current_type, next_terms, terms))
                    current_type = term.__class__
                    terms = []
                    next_terms = iter(term)
                    continue

            # Substitute variable
            if isinstance(term, V):
                term = mapping(term)
                if not isinstance(term, (_OperatorTerm, V, bool)):
                    raise SubstitutionError(
                        "Expected Variable or bool from substitution," f" got: {term!r}"
                    )

            # Check again after substitution
            if isinstance(term, V):
                variables.append(term)

            # Short circuit with booleans
            while isinstance(term, bool):
                if current_type == And:
                    if not term:
                        current_type, next_terms, terms = output_stack.pop()
                        continue
                    else:
                        break
                elif current_type == Or:
                    if term:
                        current_type, next_terms, terms = output_stack.pop()
                        continue
                    else:
                        break
                else:
                    terms.append(term)
                    break
            else:
                terms.append(term)

        return self.__class__(term, _vars=variables)

    def __repr__(self):
        arg = self._root if isinstance(self._root, bool) else str(self)
        return f"{self.__class__.__name__}({arg!r})"

    def __str__(self):
        next_terms = iter([self._root])
        output_stack = []
        current_type = None
        terms: list[_OperatorTerm | V | bool | str] = []
        term: _OperatorTerm | V | bool | str | None = None

        while True:
            try:
                term = next(next_terms)
            except StopIteration:
                term = None

            if term is None:
                if current_type is None:
                    term = terms[0]
                    break
                elif current_type == And:
                    term = " and ".join(t for t in terms)
                elif current_type == Or:
                    term = " or ".join(t for t in terms)
                current_type, next_terms, terms = output_stack.pop()

                # Break on None here to avoid wrapping the outermost term in
                # parentheses.
                if current_type is None:
                    break

                terms.append("(" + term + ")")
            else:
                if isinstance(term, _OperatorTerm):
                    output_stack.append((current_type, next_terms, terms))
                    current_type = term.__class__
                    terms = []
                    next_terms = iter(term)
                else:
                    terms.append(str(term))

        return term

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._root == other._root
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self == other
        return NotImplemented


def _parse_expression(s: str) -> _OperatorTerm:
    """Parse boolean expression containing and/or operators"""

    # Converters for opeartor clauses

    # Pairing of end group symbols with start group symbols
    group_pairs = {")": "(", "]": "["}

    scanner = re.compile(
        r"""
        (\s+) |              # space
        (\(|\[) |            # group_start
        (\)|\]) |            # group_end
        ((?:or|and)\b) |     # operator
        ([^\s\(\)\[\]]+) |   # variable
        (\Z) |               # end
        (.)                  # error
        """,
        re.DOTALL | re.VERBOSE | re.UNICODE | re.IGNORECASE,
    )

    # Parsed using two states and a stack of open clauses
    # At state 0 (not expect_operator): Expect variable, or parenthesis group
    #  start.
    # At state 1 (expect_operator): Expect operator, parenthesis group end, or
    #  end.
    expect_operator = False
    clause_stack: list[tuple[None | str, None | str, list[V]]] = []
    current_clause: list[V] = []
    clause_operator: Literal["or", "and", None] = None
    clause_symbol: Literal["(", ")", "[", "]", None] = None

    def close():
        prev_op, prev_symbol, prev_clause = clause_stack.pop()
        prev_clause.append(operators[clause_operator](*current_clause))
        return prev_op, prev_symbol, prev_clause

    operator: str
    for match in re.finditer(scanner, s):
        # print(
        #     f"{expect_operator = }\n"
        #     f"{clause_stack = }\n"
        #     f"{current_clause = }\n"
        #     f"{clause_operator = }\n"
        #     f"{clause_symbol = }\n"
        # )
        (space, group_start, group_end, operator, variable, end, error) = match.groups()
        # print(
        #     f"{space = }\n"
        #     f"{group_start = }\n"
        #     f"{group_end = }\n"
        #     f"{operator = }\n"
        #     f"{variable = }\n"
        #     f"{end = }\n"
        #     f"{error = }\n"
        # )

        if error is not None:
            raise ParseError(
                "Invalid token in expression string: {}".format(repr(match.group(0))),
                span=(match.start(), match.end()),
            )
        if space is not None:
            continue
        if expect_operator and operator is not None:
            operator = operator.lower()
            if operator == "and" and clause_operator != "and":
                prev_term: V = current_clause.pop()
                clause_stack.append((clause_operator, clause_symbol, current_clause))
                current_clause = [prev_term]
            elif operator == "or" and clause_operator == "and":
                clause_operator, clause_symbol, current_clause = close()
            clause_operator = operator  # type: ignore [assignment]
            expect_operator = False
        elif expect_operator and group_end is not None:
            if clause_operator == "and":
                clause_operator, clause_symbol, current_clause = close()
            if len(clause_stack) == 0:
                raise ParseError(
                    "Unbalanced parenthesis group in expression",
                    span=(match.start(), match.end()),
                )
            if group_pairs[group_end] != clause_symbol:
                raise ParseError(
                    "Group started with {} ended with {}".format(
                        clause_symbol, group_end
                    ),
                    span=(match.start(), match.end()),
                )
            clause_operator, clause_symbol, current_clause = close()
        elif expect_operator and end is not None:
            if clause_operator == "and":
                clause_operator, clause_symbol, current_clause = close()
        elif not expect_operator and variable is not None:
            current_clause.append(V(variable))
            expect_operator = True
        elif not expect_operator and group_start is not None:
            clause_stack.append((clause_operator, clause_symbol, current_clause))
            current_clause = []
            clause_operator = None
            clause_symbol = group_start  # type: ignore [assignment]
        else:
            raise ParseError(
                "Invalid token in expression string: {!r}".format(match.group(0)),
                span=(match.start(), match.end()),
            )

    if len(clause_stack) > 0:
        raise ParseError("Unbalanced parenthesis group in expression")

    expr = operators[clause_operator](*current_clause)
    return expr
