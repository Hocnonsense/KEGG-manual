# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 14:17:35
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-14 14:21:59
 * @FilePath: /KEGG/kegg_manual/load.py
 * @Description:
"""
# """

from pathlib import Path

import pandas as pd

from . import kmodule
from .data import query

try:
    from tqdm import tqdm
except ImportError:
    tqdm = iter


def brite_ko00001(db: str | Path | None = None):
    """Database may be download from KEGG, including the file of module and description (ko00002.json)"""

    _, brite = query.load_brite("br:ko00001", db)
    ko_levels: list[tuple[str, str, str, str, str]] = []
    levels_name: dict[str, str] = {}
    for modules1_name, modules1 in brite.items():
        name1, des1 = modules1_name.split(" ", 1)
        levels_name[name1] = des1
        for modules2_name, modules2 in modules1.items():
            name2, des2 = modules2_name.split(" ", 1)
            levels_name[name2] = des2
            for modules3_name, modules3 in modules2.items():
                if not isinstance(modules3, dict):
                    levels_name[modules3_name] = modules3
                    continue
                name3, des3 = modules3_name.split(" ", 1)
                levels_name[name3] = des3
                for KO, fns in modules3.items():
                    ko_levels.append((name1, name2, name3, KO, fns))

    ko_levels_ = pd.DataFrame(ko_levels, columns=["A", "B", "C", "KO", "name"])

    return ko_levels_, levels_name


def brite_ko00002(db: str | Path | None = None):
    """Database may be download from KEGG, including the file of module and description (ko00002.json)"""
    _, brite = query.load_brite("br:ko00002", db)
    module_levels = []
    modules = set()
    for modules1_name, modules1 in brite.items():
        for metabolism_name, metabolism in modules1.items():
            for metabolism_name2, metabolism2 in metabolism.items():
                for entry, name in metabolism2.items():
                    module_levels.append(
                        (modules1_name, metabolism_name, metabolism_name2, entry, name)
                    )
                    modules.add(entry)

    module_levels_ = pd.DataFrame(
        module_levels, columns=["A", "B", "C", "entry", "name"]
    )
    module_levels_.index = module_levels_["entry"]

    modules_d: dict[str, kmodule.KModule] = {}
    for entry in tqdm(modules):
        raw_module = query.load_module_single(entry, db, download_wait_s=0.3)
        raw_def = " ".join(i.strip() for i in raw_module["DEFINITION"])
        km = kmodule.KModule(
            raw_def,
            additional_info="".join(raw_module.get("NAME", [entry])),
        )
        modules_d[entry] = km

    return module_levels_, modules_d


def brite_ko00002_entry(db: str | Path | None = None):
    module_levels, modules = brite_ko00002(db)
    entry2ko = pd.concat(
        [
            pd.DataFrame({"entry": entry, "KO": module.kos})
            for entry, module in modules.items()
        ]
    )
    # module_levels.to_csv("data/module_levels.tsv", sep="\t", index=False)
    # entry2ko.to_csv("data/entry2ko.tsv", sep="\t", index=False)
    return module_levels, entry2ko


def brite_ko00002_gmodule(genomeko: pd.DataFrame, db: str | Path | None = None):
    _, modules = brite_ko00002(db)
    gmodule_ = (
        genomeko.apply(lambda x: x[x > 0].index, axis=0)
        .apply(
            lambda x: {
                mname: module.completeness(x) for mname, module in modules.items()
            }
        )
        .apply(lambda x: pd.Series(x))
    )
    gmodule = gmodule_.T[gmodule_.apply(sum, 0) > 0]

    return gmodule
