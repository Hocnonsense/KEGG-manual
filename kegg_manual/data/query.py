# -*- coding: utf-8 -*-
"""
 * @Date: 2021-06-14 18:41:24
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-14 14:19:40
 * @FilePath: /KEGG/kegg_manual/data/query.py
 * @Description:
"""

import json
from pathlib import Path
from time import sleep
from typing import TextIO, Union

from Bio.KEGG import REST

from . import cache


def parse_module_text(file: TextIO):
    raw_module: dict[str, list] = {}
    k = ""
    listv: list[str | tuple[str, list[str]]] = []
    for line in file:
        if line.startswith("///"):
            break
        is_k, v = line[:12].rstrip(), line[12:].strip()
        if is_k:
            if is_k.startswith("  "):
                listv = []
                raw_module[k].append((is_k.strip(), listv))
            else:
                k = is_k
                listv = raw_module.setdefault(k, [])
        if v:
            listv.append(v)
    return raw_module


def load_module_single(
    source: Union[str, TextIO], db: str | Path | None = None, download_wait_s=1
) -> dict[str, list[str]]:
    @cache.file_cached(
        lambda x: x.replace("M", "module/M"),
        lambda x: x.parent.parent / "manual" / x.parent.name / x.name,
    )
    def _load_module_txt(source: str) -> TextIO:
        assert source.startswith("M"), "not a file nor a right module number"
        assert len(source) == 6, "only single module allowed"
        sleep(download_wait_s)
        return REST.kegg_get(source)

    with _load_module_txt(source, db) as file:
        raw_module = parse_module_text(file)

    return raw_module


def read_brite_json(brite_doc):
    name: str = brite_doc["name"]
    children: str = brite_doc.get("children", "")
    if not children:
        return name.split(maxsplit=1)  # type: ignore
    return name, dict((read_brite_json(children_doc) for children_doc in children))


def load_brite(
    source: Union[str, TextIO],
    db: str | Path | None = None,
):

    @cache.file_cached(lambda x: x.replace("br:ko", "brite/ko") + ".json")
    def _load_brite_json(source: str) -> TextIO:
        assert source.startswith("br:ko"), "not a file nor a right br number"
        return REST.kegg_get(source, "json")

    with _load_brite_json(source, db) as json_in:
        brite_doc: dict[str, Union[str, list[dict]]] = json.loads(json_in.read())
        return read_brite_json(brite_doc)
