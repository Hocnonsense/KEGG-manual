# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-12 22:54:54
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-13 11:00:29
 * @FilePath: /KEGG/tests/kegg_manual/data/test_cache.py
 * @Description:
"""
# """

from time import sleep
from pathlib import Path
from kegg_manual.data import cache

try:
    from _decorator import temp_output, test_temp, test_files
except (ModuleNotFoundError, ImportError):
    from tests.kegg_manual._decorator import temp_output, test_temp, test_files


@temp_output
def test_file_modified_before(test_temp: Path):
    temp_bin = test_temp / "binny_unitem_unanimous"

    temp_bin.touch()
    sleep(1)
    assert cache.file_modified_before(temp_bin, 1)


@temp_output
def test_atom_redirect(test_temp: Path):
    temp_bin = test_temp / "binny_unitem_unanimous"
    with open(__file__) as fi:
        assert cache.atom_update_file(fi, temp_bin)

    with open(__file__) as fi:
        assert temp_bin.is_file()
        assert not cache.atom_update_file(fi, temp_bin)
    assert open(temp_bin).read() == open(__file__).read()


def report_updated_on_exit():
    cache.changed_cached_files["test"] = None  # type: ignore
