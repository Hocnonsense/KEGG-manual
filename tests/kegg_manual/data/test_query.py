# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-13 11:35:32
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-14 14:03:34
 * @FilePath: /KEGG/tests/kegg_manual/data/test_query.py
 * @Description:
"""
# """

from pathlib import Path
from kegg_manual import kmodule
from kegg_manual.data import query, cache

try:
    from _decorator import temp_output, test_temp, test_files
except (ModuleNotFoundError, ImportError):
    from tests.kegg_manual._decorator import temp_output, test_temp, test_files


def test_load_brite():
    name, brite = query.load_brite("br:ko00002", cache.db_kegg_manual_data)
    assert name == "ko00002"


def test_load_module_single():
    raw_module = query.load_module_single("M00357", cache.db_kegg_manual_data)
    if "ENTRY" in raw_module:
        assert raw_module["ENTRY"] == ["M00357            Pathway   Module"]
    # may be problematic:
    # M00651


manual_updated_modules = [
    "M00651",
    "M00745",
]


@temp_output
def test_cached_modules(test_temp: Path, update_maunal=False):
    db: Path = cache.db_kegg_manual_data

    with open(test_temp / "a", "w") as f1, open(test_temp / "b", "w") as f2:
        for entry_file in sorted((db / "module").glob("M*")):
            entry = entry_file.name

            if len(entry) != 6:
                continue
            with open(entry_file) as fi:
                raw_module = query.parse_module_text(fi)

            raw_def = " ".join(i.strip() for i in raw_module["DEFINITION"])
            km = kmodule.KModule(
                raw_def,
                additional_info="".join(raw_module.get("NAME", [entry])),
            )
            entry_file_manual = (
                entry_file.parent.parent
                / "manual"
                / entry_file.parent.name
                / entry_file.name
            )

            assert str(km) == str(kmodule.KModule(str(km)))
            assert (
                str(km).replace("+", " ").replace("-", " ")
                != raw_def.replace(" --", "")
                .replace("-- ", "")
                .replace("+", " ")
                .replace("-", " ")
            ) == entry_file_manual.is_file()
            if entry_file_manual.is_file():
                with open(entry_file_manual) as fi:
                    raw_module_manual = query.parse_module_text(fi)

                raw_def_manual = " ".join(
                    i.strip() for i in raw_module_manual["DEFINITION"]
                )
                km_manual = kmodule.KModule(
                    raw_def_manual,
                    additional_info="".join(raw_module_manual.get("NAME", [entry])),
                )
                print(entry, km, "\n", file=f1)
                print(entry, raw_def, "\n", file=f2)
                assert (str(km) != str(km_manual)) == (entry in manual_updated_modules)
                assert str(km_manual) == raw_def_manual
                assert (
                    query.load_module_single(entry, db=db)["DEFINITION"]
                    == raw_module_manual["DEFINITION"]
                )

    if update_maunal:
        with open(test_temp / "c", "w") as fo, open(test_temp / "a") as fi:
            fo.write(fi.read())

        # you should manual update [test_temp / "c"](tests/kegg_manual/temp/c)
        to_update = (
            input(f"Update module from {test_temp / 'c'}?\n[yes/N]: ").lower() == "yes"
        )
        if to_update:
            with open(test_temp / "c") as fi:
                for line in fi:
                    line = line.strip()
                    if not line:
                        continue
                    entry, raw_def = line.split(maxsplit=1)
                    with open(db / "manual" / "module" / entry, "w") as fo:
                        print(f"DEFINITION  {raw_def}", file=fo)
                        print(f"///", file=fo)
