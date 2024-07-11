# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-12 22:54:54
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-07-11 11:35:44
 * @FilePath: /KEGG/tests/kegg_manual/data/test_cache.py
 * @Description:
"""
# """

from time import sleep
from kegg_manual.data import cache

from tests import Path, temp_output, test_files, test_temp


@temp_output
def test_data_config(test_temp: Path):
    cfg = cache.data_config()
    cfg2 = cache.data_config()
    assert cfg.config == cfg2.config
    cfg(db_kegg_manual_data=test_temp / "test", db_kegg_manual_verbose=False)
    assert cfg.config != cfg2.config
    with open(cfg()(test_temp / "test.yaml")) as fi:
        assert set(fi) == {
            "db_kegg_manual_verbose: 'false'\n",
            f"db_kegg_manual_data: {test_temp/ 'test'}\n",
        }
    cfg3 = cache.data_config()
    assert cfg.config == cfg3.config
    assert cache.db_kegg_manual_data == test_temp / "test"
    cfg2()
    assert cache.db_kegg_manual_data != test_temp / "test"


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
