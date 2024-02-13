# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-13 11:35:32
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-13 13:22:50
 * @FilePath: /KEGG/tests/kegg_manual/data/test_query.py
 * @Description:
"""
# """

from kegg_manual.data import query, cache


def test_load_brite():
    name, brite = query.load_brite("br:ko00002", cache.db_kegg_manual_data)
    assert name == "ko00002"


def test_load_module_single():
    raw_module = query.load_module_single("M00357", cache.db_kegg_manual_data)
    assert raw_module["ENTRY"] == ["M00357            Pathway   Module"]
