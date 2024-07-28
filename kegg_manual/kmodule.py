# -*- coding: utf-8 -*-
"""
 * @Date: 2020-07-01 00:29:24
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-07-28 17:44:54
 * @FilePath: /KEGG/kegg_manual/kmodule.py
 * @Description:
"""

from typing import Iterable, Literal, Optional, Sequence

import logging

logger = logging.getLogger(__name__)


def rget_sub(express: str, p: int):
    bracket_stack = 1
    plb = express.rfind("(", 0, p)
    prb = express.rfind(")", 0, p)
    while bracket_stack:
        if plb < prb:
            bracket_stack += 1
            p = prb
            prb = express.rfind(")", 0, p)
        else:
            bracket_stack -= 1
            p = plb
            plb = express.rfind("(", 0, p)
    return p


class KModule:
    """
    @description:
        KEGG module units
        It contains the functions in elements.

        if self.ko, then assert not self._elements, vice versa.
    """

    def __init__(self, express="", additional_info=""):
        self.additional_info = additional_info
        self.steps: list[KModule]
        self._ko, self.steps, self._is_chain = self.__calculate(express)

    @classmethod
    def __calculate(cls, express: str):
        """Calculate express"""
        _is_chain = True
        if not express:
            return express, [], _is_chain

        logger.debug(f"| 1. decode {express} <")
        express_ = express.strip("-").strip("+")
        p = len(express_) - 1
        if p == 5:  # ko
            logger.debug(f"|> 2.   KO {express_} detected")
            return express_, [], _is_chain

        # this time, we first remove all sub modules with bracket
        subexpresses: dict[str, str] = {}
        while ")" in express_:
            c = express_[p]
            if c in ")":  # you are trapped into a sub element
                last_p = p
                p = rget_sub(express_, p)
                subentry = f"{p:X>6}"
                subexpresses[subentry] = express_[p + 1 : last_p]
                express_ = express_[:p] + subentry + express_[last_p + 1 :]
                logger.debug(
                    f"|>> 3.1 sub {subexpresses[subentry]} detected as {subentry} "
                    + ("-" * 5)
                    + f" {express_[:p]}>{express_[p:]}",
                )
            p -= 1

        logger.debug(
            f"|>> 3.2 sub {express_[:p]}>{express_[p:]} " + ("-" * 5) + f" {express}",
        )

        def update_subexpress(express_: str):
            if express_ in subexpresses:
                return subexpresses[express_]
            for subentry in subexpresses:
                if subentry in express_:
                    express_ = express_.replace(subentry, f"({subexpresses[subentry]})")
            return express_

        if "," in express_:
            _is_chain = False
            elements = [cls(update_subexpress(x)) for x in express_.split(",")]
            logger.debug(f"|>> 4.1 `,` {_is_chain}; elements {elements}")
        elif " " in express_:
            elements = [
                cls(update_subexpress(x))
                for x in express_.split(" ")
                if x.replace("+", "-").strip("-")
            ]
            logger.debug(f"|>> 4.2 ` ` {_is_chain}; elements {elements}")
        else:
            elements = [
                cls(update_subexpress(x))
                for x in express_.replace("-", "+").strip("+").split("+")
            ]
            logger.debug(f"|>> 4.3 `+` {_is_chain}; elements {elements}")

        if len(elements) == 1 and elements[0]._is_chain and not elements[0]._ko:
            elements = elements[0].steps

        logger.debug(f"|> 5. exp: {express}")
        logger.debug(f"...   str: {cls.str2(('', elements, _is_chain), ' ')}")
        return "", elements, _is_chain

    def list_ko(self) -> list[str]:
        if self._ko:
            return [self._ko]
        kos = [ko for element in self.steps for ko in element.list_ko()]
        return sorted(set(kos), key=kos.index)

    kos = property(fget=list_ko)

    @property
    def nsteps(self):
        if self._ko:
            return 1
        return len(self.steps)

    def __len__(self):
        return sum([len(e) for e in self.steps]) if self.steps else 1

    def __getitem__(self, key: str):
        """
        Return a way contains it

        >>> e, i = KModule(
        ...     "K00826 ((K00166+K00167,K11381)+K09699+K00382) "
        ...     "(K00253,K00249) (K01968+K01969) (K05607,K13766) K01640"
        ... )["K00382"]
        >>> i
        [1, 2, 0]
        >>> e[1][2][0]
        "K00382"
        """
        if key == self._ko:
            return [self._ko], [0]
        for e in self.steps:
            e_key, i_key = e[key]
            if i_key != [-1]:
                if self._is_chain:  # all elements is important
                    e_key = [
                        e_key if e_chain is e else e_chain for e_chain in self.steps
                    ]
                    i_key = [self.steps.index(e)] + i_key
                return e_key, i_key
        return [], [-1]

    def str2(
        self: "KModule|tuple[str, list[KModule], bool]",
        sep_chain: Literal[" ", "+", "-"] = "+",
    ):
        _ko, steps, _is_chain = (
            (self._ko, self.steps, self._is_chain)
            if isinstance(self, KModule)
            else self
        )
        if _ko:
            return _ko
        sep = sep_chain if _is_chain else ","
        kids = []
        for kid in steps:
            if kid._ko:
                kids.append(str(kid))
            elif kid._is_chain and sep == ",":
                kids.append(str(kid))
            elif kid._is_chain and sep == " ":
                kids.append(kid.str2("+"))
            else:
                kids.append("(" + str(kid) + ")")
        return sep.join(kids)

    def __str__(self):
        return self.str2(" ")

    def __repr__(self):
        return f"`{self}`"

    @classmethod
    def from_list(cls, no_comma: list["KModule"], is_chain=True, additional_info=""):
        """New Element by a list"""
        if len(no_comma) == 1:
            e = no_comma[0]
        else:
            e = KModule()
            e.steps = no_comma
            e._is_chain = is_chain
            e.additional_info = additional_info
        return e

    def all_paths(self, ko_match: Optional[Sequence[str]] = None) -> list[str]:
        """
        module.all_paths():
            return all potential metabolism paths with KO
        module.all_paths(ko_match):
            return all available metabolism paths if KO be found in ko_match
        """
        if self._is_chain:
            if self._ko:
                if ko_match is None or self._ko in ko_match:
                    return [self._ko]
                return []  # this KO is not in list/dict/set, should not be detected
            last_paths = [""]
            for kid in self.steps:
                paths = kid.all_paths(ko_match)
                if not paths:
                    return []
                last_paths = [
                    f"{last_path} {path}" if last_path else path
                    for last_path in last_paths
                    for path in paths
                ]
            return last_paths
        else:
            paths = [path for kid in self.steps for path in kid.all_paths(ko_match)]
            if paths == []:
                return []
            len_path = max(len(path) for path in paths)
            paths = sorted(
                {
                    "[{path:^{len_path}}]".format(path=path, len_path=len_path)
                    for kid in self.steps
                    for path in kid.all_paths(ko_match)
                }
            )
            return paths

    def abundance(self, ko_match: dict[str, float | int]):
        return sum(ko_match.get(ko, 0) for ko in self.list_ko())

    def completeness(self, ko_match: Iterable[str]) -> float:
        """Complessness of given match, ko is its dict"""
        count = 0.0
        if self._ko:
            return 1 if self._ko in ko_match else 0
        # multipy elements
        if self._is_chain:
            for element in self.steps:
                count += element.completeness(ko_match)
            return count / len(self.steps)
        # self.is_chain is False
        return max([element.completeness(ko_match) for element in self.steps])
