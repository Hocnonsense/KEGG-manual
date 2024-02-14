# -*- coding: utf-8 -*-
"""
 * @Date: 2020-07-01 00:29:24
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-14 14:01:58
 * @FilePath: /KEGG/kegg_manual/kmodule.py
 * @Description:
"""
import pickle
from io import StringIO
from typing import Iterable, Literal, Optional, Sequence, TextIO, Union

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

        if self.ko, then assert not self.elements, vice versa.
    """

    def __init__(self, express="", additional_info=""):
        self._is_chain = True
        self._elements: list[KModule] = []
        self._ko = ""
        self.additional_info = additional_info

        self.__calculate(express)

    def __calculate(self, express: str):
        """Calculate express"""
        if not express:
            return

        logger.debug(f"| 1. decode {express} <")
        express_ = express.strip("-").strip("+")
        p = len(express_) - 1
        if p == 5:  # ko
            logger.debug(f"|> 2.   KO {express_} detected")
            self._ko = express_
            return

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

        elements: list[KModule] = []
        if "," in express_:
            self._is_chain = False
            elements = [KModule(update_subexpress(x)) for x in express_.split(",")]
            logger.debug(f"|>> 4.1 `,` {self._is_chain}; elements {elements}")
        elif " " in express_:
            elements = [
                KModule(update_subexpress(x))
                for x in express_.split(" ")
                if x.replace("+", "-").strip("-")
            ]
            logger.debug(f"|>> 4.2 ` ` {self._is_chain}; elements {elements}")
        else:
            elements = [
                KModule(update_subexpress(x))
                for x in express_.replace("-", "+").strip("+").split("+")
            ]
            logger.debug(f"|>> 4.3 `+` {self._is_chain}; elements {elements}")
        if len(elements) == 1 and elements[0]._is_chain and not elements[0]._ko:
            self._elements.extend(elements[0]._elements)
        else:
            self._elements.extend(elements)

        logger.debug(f"|> 5. exp: {express}")
        logger.debug(f"...   str: {self}")

    def list_ko(self) -> list[str]:
        if self._ko:
            return [self._ko]
        return [ko for element in self._elements for ko in element.list_ko()]

    kos = property(fget=list_ko)

    def __len__(self):
        return sum([len(e) for e in self._elements]) if self._elements else 1

    def __getitem__(self, key: str):
        """
        Return a way contains it

        >>> e, i = KModule(
        ... "K00826 ((K00166+K00167,K11381)+K09699+K00382) (K00253,K00249) (K01968+K01969) (K05607,K13766) K01640"
        ... )["K00382"]
        >>> i
        [1, 2, 0]
        >>> e[1][2][0]
        "K00382"
        """
        if key == self._ko:
            return [self._ko], [0]
        for e in self._elements:
            e_key, i_key = e[key]
            if i_key != [-1]:
                if self._is_chain:  # all elements is important
                    e_key = [
                        e_key if e_chain is e else e_chain for e_chain in self._elements
                    ]
                    i_key = [self._elements.index(e)] + i_key
                return e_key, i_key
        return [], [-1]

    def str2(self, sep_chain: Literal[" ", "+", "-"] = "+"):
        if self._ko:
            return self._ko
        sep = sep_chain if self._is_chain else ","
        kids = []
        for kid in self._elements:
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
            e._elements = no_comma
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
            for kid in self._elements:
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
            paths = [path for kid in self._elements for path in kid.all_paths(ko_match)]
            if paths == []:
                return []
            len_path = max(len(path) for path in paths)
            paths = sorted(
                {
                    "[{path:^{len_path}}]".format(path=path, len_path=len_path)
                    for kid in self._elements
                    for path in kid.all_paths(ko_match)
                }
            )
            return paths

    def abundance(self, ko_match: dict[str, Union[float, int]]):
        return sum(ko_match.get(ko, 0) for ko in self.list_ko())

    def completeness(self, ko_match: Iterable) -> float:
        """Complessness of given match, ko is its dict"""
        count = 0.0
        if self._ko:
            return 1 if self._ko in ko_match else 0
        # multipy elements
        if self._is_chain:
            for element in self._elements:
                count += element.completeness(ko_match)
            return count / len(self._elements)
        # self.is_chain is False
        return max([element.completeness(ko_match) for element in self._elements])


def init_module(module_str: Union[str, StringIO, TextIO]):
    """
    @description: init modules
    @param module_str:
        string or IO of modules from KEGG module
        e.g. Amino_acid_metabolism
    @return module{metabolism: {Entry: KModule(Definition)}}
    """
    if not isinstance(module_str, str):
        module_str_ = module_str
    else:
        module_str_ = StringIO(module_str)

    module: dict[str, dict[str, KModule]] = {}
    title = ""
    line = module_str_.readline()
    while line:
        if line.strip()[0:5] == "Entry":
            Entry = line.split()[1]
            line = module_str_.readline()
            Name = " ".join(line.strip().split()[1:])
            # Name = Name[: Name.find(",")]
            line = module_str_.readline()
            express = " ".join(line.strip().split()[1:])
            module[title][Entry] = KModule(express, Name)
        else:  # title
            title = line.strip()[:-1]
            if title:
                module[title] = {}
        line = module_str_.readline()

    return module


def _load_module(module_name):
    """
    @description: load module by pickle files or text files
    """
    try:
        pin = open(module_name + ".pickle", "rb")
        module = pickle.load(pin)
    except (OSError, FileNotFoundError, EOFError) as exc:
        if getattr(exc, "errno", None) != 36:  # file too long :)
            raise
        module = init_module(module_name)
        # with open(module_name + ".pickle", "wb") as pout:
        #     pickle.dump(module, pout)
    return module
