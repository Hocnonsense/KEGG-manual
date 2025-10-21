# -*- coding: utf-8 -*-
"""
* @Date: 2021-06-14 18:41:24
* @LastEditors: hwrn hwrn.aou@sjtu.edu.cn
* @LastEditTime: 2025-10-21 21:55:13
* @FilePath: /KEGG-manual/kegg_manual/data/query.py
* @Description:
"""

from dataclasses import dataclass
import json
from typing import Any, TextIO, Union

from Bio.KEGG import REST


from . import cache
from .. import entry, utils


@dataclass
class CachedKBrite(cache.CachedModified):
    def func_to_file(self, source) -> str:
        return source.replace("br:ko", "brite/ko") + ".json"

    def rsync_io(self, source):
        self.sleep()
        return REST.kegg_get(source, "json")

    def load(self, source) -> tuple[str, dict[str, Any]]:
        return super().load(source)

    def parse_io(self, io_in):
        brite_doc: dict[str, Union[str, list[dict]]] = json.loads(io_in.read())
        return self.read_brite_json(brite_doc)

    def check_source_valid(self, source):
        assert source.startswith("br:ko"), "not a file nor a right br number"
        return True

    @classmethod
    def read_brite_json(cls, brite_doc):
        name: str = brite_doc["name"]
        children: str = brite_doc.get("children", "")
        if not children:
            return name.split(maxsplit=1)  # type: ignore
        return name, dict(
            (cls.read_brite_json(children_doc) for children_doc in children)
        )


kbritedb = CachedKBrite(db=cache.manual_config.database)


@dataclass
class CachedKEntry(cache.CachedModified):
    def __post_init__(self) -> None:
        if self.func_to_file_modify is None:
            self.func_to_file_modify = self.redirect_modify
        return super().__post_init__()

    def rsync_io(self, source) -> TextIO:
        self.sleep()
        return REST.kegg_get(source)

    def load(self, source) -> dict[str, list[str | tuple[str, list[str]]]]:
        return super().load(source)

    def parse_io(self, io_in):
        return next(entry.KEntry.yield_from_testio(io_in)).properties


@dataclass
class CachedKModule(CachedKEntry):
    def func_to_file(self, source):
        return source.replace("M", "module/M")

    def check_source_valid(self, source):
        assert source.startswith("M"), "not a file nor a right module number"
        assert len(source) == 6, "only single module allowed"
        return True


kmoduledb = CachedKModule(db=cache.manual_config.database)


@dataclass
class CachedKO(CachedKEntry):
    def func_to_file(self, source):
        return source.replace("K", "ko/K")

    def check_source_valid(self, source):
        assert source.startswith("K"), "not a file nor a right ko number"
        assert len(source) == 6, "only single module allowed"
        return True

    def link_reacion(self, rxn_mapping: dict[str, list[str]]):
        """
        Functions converts gene associations to KO into gene
        associations for reaction IDs. Returns a dictionary
        of Reaction IDs to genes.
        """
        rxn_dict: dict[str, set] = {}
        for ko, genes in rxn_mapping.items():
            reaction = self.load(ko)
            for i in reaction.get("DBLINKS", []):
                if isinstance(i, str) and i.startswith("RN"):
                    for r in i.split()[1:]:
                        if r.startswith("R"):
                            rxn_dict.setdefault(r, set()).update(genes)
            for i in reaction.get("REACTION", []):
                if isinstance(i, str) and i.startswith("R"):
                    for r in i.split(maxsplit=1)[0].split(","):
                        rxn_dict.setdefault(r, set()).update(genes)
        return rxn_dict


kodb = CachedKO(db=cache.manual_config.database)


@dataclass
class CachedKEC(CachedKEntry):
    def func_to_file(self, source):
        return f"ec/{source}"

    def check_source_valid(self, source):
        assert source.count(".") == 3 or "-" in source
        return True

    def link_reacion(self, rxn_mapping: dict[str, list[str]]):
        """
        Functions converts gene associations to EC into gene
        associations for reaction IDs. Returns a dictionary
        of Reaction IDs to genes.
        """
        rxn_dict: dict[str, set] = {}
        for ko, genes in rxn_mapping.items():
            reaction = self.load(ko)
            for i in reaction.get("ALL_REAC", []):
                if isinstance(i, str) and i.startswith("R"):
                    for r in i.split():
                        if r.startswith("R"):
                            rxn_dict.setdefault(r, set()).update(genes)
        return rxn_dict


kecdb = CachedKEC(db=cache.manual_config.database)


@dataclass
class CachedKCompound(CachedKEntry):
    rhea: utils.RheaDb | None = None

    def func_to_file(self, source):
        return source.replace("C", "compound/C")

    def check_source_valid(self, source):
        assert source.startswith("C"), "not a file nor a right compound number"
        assert len(source) == 6, "only single module allowed"
        return True

    def load(self, source) -> entry.KCompound:  # type: ignore [override]
        return super().load(source)  # type: ignore [return-value]

    def parse_io(self, io_in):  # type: ignore [reportIncompatibleMethodOverride]
        e = next(entry.KCompound.yield_from_testio(io_in, rhea=self.rhea))
        return entry.KCompound(e.properties)  # type: ignore [reportArgumentType]


kcompounddb = CachedKCompound(db=cache.manual_config.database)
