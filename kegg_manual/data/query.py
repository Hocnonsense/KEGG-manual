# -*- coding: utf-8 -*-
"""
 * @Date: 2021-06-14 18:41:24
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 00:40:17
 * @FilePath: /KEGG/kegg_manual/data/query.py
 * @Description:
"""

from dataclasses import dataclass
import json
from typing import TextIO, Union

from Bio.KEGG import REST


from . import cache
from .. import entry, utils


@dataclass
class CachedKBrite(cache.CachedModified):

    def __post_init__(self) -> None:
        if self.func_to_file is None:
            self.func_to_file = lambda x: x.replace("br:ko", "brite/ko") + ".json"
        return super().__post_init__()

    def _get_io(self, source: str) -> TextIO:
        super()._get_io(source)
        return REST.kegg_get(source, "json")

    def load_single(self, source: str) -> tuple[str, dict[str, dict]]:
        return super().load_single(source)

    def load_single_from_io(self, file: TextIO):
        brite_doc: dict[str, Union[str, list[dict]]] = json.loads(file.read())
        return self.read_brite_json(brite_doc)

    def check_source_valid(self, source: str):
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


kbritedb = CachedKBrite(db=cache.db_kegg_manual_data)


@dataclass
class CachedKEntry(cache.CachedModified):
    def __post_init__(self) -> None:
        if self.func_to_file_modify is None:
            self.func_to_file_modify = (
                lambda x: x.parent.parent / "manual" / x.parent.name / x.name
            )
        return super().__post_init__()

    def _get_io(self, source: str) -> TextIO:
        super()._get_io(source)
        return REST.kegg_get(source)

    def load_single(self, source: str) -> dict[str, list[str | tuple[str, list[str]]]]:
        return super().load_single(source)

    def load_single_from_io(self, file: TextIO):
        return next(entry.KEntry.yield_from_testio(file)).properties


@dataclass
class CachedKModule(CachedKEntry):
    def __post_init__(self) -> None:
        if self.func_to_file is None:
            self.func_to_file = lambda x: x.replace("M", "module/M")
        return super().__post_init__()

    def check_source_valid(self, source: str):
        assert source.startswith("M"), "not a file nor a right module number"
        assert len(source) == 6, "only single module allowed"
        return True


kmoduledb = CachedKModule(db=cache.db_kegg_manual_data)


@dataclass
class CachedKO(CachedKEntry):
    def __post_init__(self) -> None:
        if self.func_to_file is None:
            self.func_to_file = lambda x: x.replace("K", "ko/K")
        return super().__post_init__()

    def check_source_valid(self, source: str):
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
            reaction = self.load_single(ko)
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


kodb = CachedKO(db=cache.db_kegg_manual_data)


@dataclass
class CachedKEC(CachedKEntry):
    def __post_init__(self) -> None:
        if self.func_to_file is None:
            self.func_to_file = lambda x: f"ec/{x}"
        return super().__post_init__()

    def check_source_valid(self, source: str):
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
            reaction = self.load_single(ko)
            for i in reaction.get("ALL_REAC", []):
                if isinstance(i, str) and i.startswith("R"):
                    for r in i.split():
                        if r.startswith("R"):
                            rxn_dict.setdefault(r, set()).update(genes)
        return rxn_dict


kecdb = CachedKEC(db=cache.db_kegg_manual_data)


@dataclass
class CachedKCompound(CachedKEntry):
    rhea: utils.RheaDb | None = None

    def __post_init__(self) -> None:
        if self.func_to_file is None:
            self.func_to_file = lambda x: x.replace("C", "compound/C")
        return super().__post_init__()

    def check_source_valid(self, source: str):
        assert source.startswith("C"), "not a file nor a right compound number"
        assert len(source) == 6, "only single module allowed"
        return True

    def load_single(self, source: str) -> entry.KCompound:  # type: ignore [override]
        return super().load_single(source)  # type: ignore [return-value]

    def load_single_from_io(self, file: TextIO):
        e = next(entry.KCompound.yield_from_testio(file, rhea=self.rhea))
        return entry.KCompound(e.properties, e.filemark)


kcompounddb = CachedKCompound(db=cache.db_kegg_manual_data)
