# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-14 21:56:31
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-14 23:15:38
 * @FilePath: /KEGG/tests/kegg_manual/test_entry.py
 * @Description:
"""
# """

from io import StringIO

from kegg_manual import entry


def test_check_entry_key_indend():
    assert entry.check_entry_key_indend("ENTRY     ID001") == 10
    assert (
        entry.check_entry_key_indend("ENTRY       M00006            Pathway   Module\n")
        == 12
    )
    try:
        entry.check_entry_key_indend("          property!")
    except entry.ParseError:
        pass
    else:
        assert False


def test_entry_yield_from_testio():
    f = StringIO(
        "\n".join(
            [
                "ENTRY     ID001",
                "NAME      Test entry",
                "PROPERTY  This is a multi-line",
                "          property!",
                "///",
                "ENTRY     ID002",
                "NAME      Another entry",
                "PROPERTY  Single line property",
                "REFS      ref1: abcdef",
                "          ref2: defghi",
                "///",
            ]
        )
    )
    entries = list(entry.KEntry.yield_from_testio(f))
    assert len(entries) == 2
    assert entries[0].properties == {
        "ENTRY": ["ID001"],
        "NAME": ["Test entry"],
        "PROPERTY": ["This is a multi-line", "property!"],
    }
    assert entries[1].properties == {
        "ENTRY": ["ID002"],
        "NAME": ["Another entry"],
        "PROPERTY": ["Single line property"],
        "REFS": ["ref1: abcdef", "ref2: defghi"],
    }
