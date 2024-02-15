# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 21:16:17
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-15 11:33:13
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


from typing import TextIO
import re
from . import utils


class ParseError(Exception):
    """Exception used to signal errors while parsing"""


def check_entry_key_indend(line: str, lineno: int | None = None):
    m = re.match(r"([A-Z_]+\s+)(.*)", line.rstrip())
    if m is not None:
        return len(m.group(1))
    else:
        raise ParseError(f"Cannot determine key length at line {lineno} `{line}`")


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
    def yield_from_testio(cls, f: TextIO, context=None):
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
                yield cls(properties, filemark=mark)
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
