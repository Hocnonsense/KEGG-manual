# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 14:22:57
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-14 14:25:31
 * @FilePath: /KEGG/tests/kegg_manual/test_load.py
 * @Description:
"""
# """

from kegg_manual import load
from kegg_manual.data import cache


def test_brite_ko00002():
    module_levels, modules = load.brite_ko00002(cache.db_kegg_manual_data)
    ko_abd = {
        "K19746": 0.0,
        "K19744": 1.0,
        "K12658": 2.0,
        "K21060": 3.0,
        "K22549": 4.0,
        "K21061": 5.0,
        "K22550": 6.0,
        "K21062": 7.0,
        "K13877": 8.0,
    }
    assert (
        modules["M00947"].abundance(ko_abd),
        modules["M00947"].completeness(ko_abd),
        modules["M00947"].completeness(
            {ko: abd for ko, abd in ko_abd.items() if abd > 0}
        ),
    ) == (1.0, 1.0, 0.5)
    assert (
        modules["M00948"].abundance(ko_abd),
        modules["M00948"].completeness(ko_abd),
    ) == (35.0, 1.0)
