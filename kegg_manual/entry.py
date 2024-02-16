# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 21:16:17
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 14:01:00
 * @FilePath: /KEGG/kegg_manual/entry.py
 * @Description:
    Representation of compound/reaction entries in models.
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

Copyright 2016-2017  Jon Lund Steffensen <jon_steffensen@uri.edu>
Copyright 2015-2020  Keith Dufault-Thompson <keitht547@my.uri.edu>
Copyright 2020-2020  Elysha Sameth <esameth1@my.uri.edu>
"""
# """


import logging
from typing import TextIO
import re
from . import utils, formula

logger = logging.getLogger(__name__)

try:
    from libchebipy._chebi_entity import ChebiEntity  # type: ignore [reportMissingImports]

    use_chebi = True
except ImportError:
    logger.warning(
        "WARNING: The Chebi API package not found! " "Some functions will be unusable"
    )
    use_chebi = False


def check_entry_key_indend(line: str, lineno: int | None = None):
    m = re.match(r"([A-Z_]+\s+)(.*)", line.rstrip())
    if m is not None:
        return len(m.group(1))
    else:
        raise utils.ParseError(f"Cannot determine key length at line {lineno} `{line}`")


class KEntry(utils.ModelEntry):
    """Base class for KEGG entry with raw values from KEGG."""

    def __init__(self, properties: dict, filemark=None):
        self._properties: dict[str, list[str | tuple[str, list[str]]]] = (
            utils.FozenDict(properties)  # type: ignore [assignment]
        )
        self._filemark = filemark
        entry = self._properties.get("ENTRY", [""])[0]
        assert isinstance(entry, str)
        self._id = entry.split("  ", 1)[0]

    @property
    def id(self):
        return self._id

    @property
    def properties(self):
        return self._properties

    @property
    def filemark(self):
        return self._filemark

    @classmethod
    def yield_from_testio(cls, f: TextIO, context=None, **kwargs):
        """Iterate over entries in KEGG file."""
        entry_line: int = None  # type: ignore [assignment]
        key_length = 0
        properties: dict[str, list[str | tuple[str, list[str]]]] = {}
        section_id = ""
        section_vs: list[str | tuple[str, list[str]]] = []
        for lineno, line in enumerate(f):
            if line.strip() == "///":
                # End of entry
                mark = utils.FileMark(context, entry_line, 0)
                yield cls(properties, filemark=mark, **kwargs)
                properties = {}
                section_id = ""
                entry_line = None  # type: ignore [assignment]
                key_length = 0
            else:
                if not line.strip():
                    continue

                if entry_line is None:
                    entry_line = lineno
                if not key_length:
                    key_length = check_entry_key_indend(line, lineno)

                is_k, v = line[:key_length].rstrip(), line[key_length:].strip()
                if is_k:
                    if is_k.startswith("  "):
                        section_vs_1: list[str] = []
                        properties[section_id].append((is_k.strip(), section_vs_1))
                        section_vs = section_vs_1  # type: ignore [assignment]
                    else:
                        section_id = is_k
                        section_vs = properties.setdefault(section_id, [])
                if v:
                    section_vs.append(v)


class KCompound(KEntry):
    """Representation of entry in KEGG compound file"""

    def __init__(
        self,
        properties: dict[str, list[str]],
        filemark=None,
        rhea: utils.RheaDb | None = None,
    ):
        super().__init__(properties, filemark)

        if "ENTRY" not in self.properties:
            raise KeyError("Missing compound identifier")
        self._id = properties["ENTRY"][0].split(maxsplit=1)[0]

        self._formula = ""
        self._charge: int | None = None
        self._chebi: str = ""
        self._chebi_all: set[str] = set()
        self.rhea = rhea
        self.initialize_charge()

    def initialize_charge(self):
        """
        Sets the _charge, _chebi, and _chebi_all attributes
        'rhea_db' is initialized as a global in generate_model_api
        if --rhea is supplied this funcion looks for rhea_db in the
        global namespace decide if rhea is used
        --- Logic for selecting the best chebi ID ---
        if not using rhea:
            use the first chebi ID given by KEGG
        elif using rhea:
            if all KEGG-chebi IDs map to same ID in rhea:
                use the single ID
            elif KEGG-chebi IDs map to different IDs in rhea:
                use the first chebi ID given by KEGG
            elif the KEGG-chebi IDs don't have mappings in rhea:
                use the first chebi ID given by KEGG
        """
        if self.rhea is not None:
            use_rhea = True
            rhea_db = self.rhea
        else:
            use_rhea = False
        for DB, ID in self.dblinks:
            if DB == "ChEBI":
                id_list = ID.split(" ")
                if use_rhea:
                    rhea_id_list = rhea_db.select_chebi_id(id_list)
                    if len(rhea_id_list) == 0:  # no chebis map to rhea
                        self._chebi = id_list[0]
                        self._chebi_all = set(id_list)
                    elif len(set(rhea_id_list)) == 1:  # chebi map to same rhea
                        self._chebi = rhea_id_list[0]
                        self._chebi_all = set(id_list + [rhea_id_list[0]])
                    else:  # chebis map to different rheas
                        self._chebi = id_list[0]
                        self._chebi_all = set(id_list + rhea_id_list)
                else:  # --rhea not given
                    self._chebi = id_list[0]
                    self._chebi_all = set(id_list)

        # libchebipy update charge and formula
        if self._chebi != "" and use_chebi:
            self.update_charge_formula()

    if use_chebi:

        def update_charge_formula(self):
            this_chebi_entity = ChebiEntity(self._chebi)
            try:
                try:
                    # libchebipy sometimes fails with an index error
                    # on the first time running. We have not been able
                    # to fix the source of this error, but catching the
                    # index error and repeating the operation appears to
                    # fix this
                    self._charge = int(this_chebi_entity.get_charge())
                    self._formula = this_chebi_entity.get_formula()
                except IndexError:
                    self._charge = int(this_chebi_entity.get_charge())
                    self._formula = this_chebi_entity.get_formula()
            except ValueError:  # chebi entry has no charge; leave as None
                pass

    else:

        def update_charge_formula(self):
            pass

    @property
    def name(self):
        try:
            return next(self.names)
        except StopIteration:
            return None

    @property
    def names(self):
        for line in self.properties.get("NAME", []):
            for name in line.rstrip(";").split(";"):
                yield name.strip()

    @property
    def reactions(self):
        for line in self.properties.get("REACTION", []):
            for rxnid in line.split():
                yield rxnid

    @property
    def enzymes(self):
        for line in self.properties.get("ENZYME", []):
            for enzyme in line.split():
                yield enzyme

    @property
    def formula(self):
        return self._formula or self.properties.get("FORMULA", [None])[0]

    @property
    def mol_weight(self):
        if "MOLWEIGHT" not in self.properties:
            return None
        return float(self.properties["MOLWEIGHT"][0])

    @property
    def dblinks(self):
        for line in self.properties.get("DBLINKS", []):
            database, entry = line.split(":", 1)
            yield database.strip(), entry.strip()

    @property
    def charge(self):
        return self._charge

    @property
    def chebi(self):
        return self._chebi

    @property
    def chebi_all(self):
        if self._chebi_all is not None:
            return ", ".join(self._chebi_all)
        else:
            return None

    @property
    def comment(self):
        comment = self.properties.get("COMMENT")
        if not comment:
            return None
        try:
            return "\n".join(comment)
        except TypeError:
            return comment

    def __getitem__(self, name):
        if name not in self.properties:
            raise AttributeError("Attribute does not exist: {}".format(name))
        return self.properties[name]

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.id}">'

    def is_generic(self):
        """
        Function for checking if the compound formulation is compatible with psamm.

        generalized rules for this are that compounds
        - must have a formula,
        - the formula cannot be variable (e.g. presence of X),
        - and R groups are generally discouraged.
        """
        if self.formula is None:
            return True
        if "R" in str(self.formula):
            return True
        try:
            form = formula.Formula.parse(str(self.formula))
            return form.is_variable()
        except utils.ParseError:
            return True
