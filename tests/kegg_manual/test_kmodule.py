# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-12 11:22:41
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-16 13:13:44
 * @FilePath: /KEGG/tests/kegg_manual/test_kmodule.py
 * @Description:
"""
# """

from kegg_manual import kmodule


def test_logger_debug():
    kmodule.logger.addHandler(kmodule.logging.StreamHandler())
    kmodule.logger.setLevel(-1)


def test_kmodule_express():
    def echo(express: str, updated_express: str | None = None):
        """repeat the express"""
        km = kmodule.KModule(express)

        assert str(km) == str(kmodule.KModule(str(km)))
        assert len(km) == express.count("K")

        if updated_express is not None:
            assert str(km) == updated_express
        else:
            assert str(km) == express

    for s in (
        "K00058 K00831 (K01079,K02203,K22305)",
        "(K00928,K12524,K12525,K12526) K00133 (K00003,K12524,K12525) (K00872,K02204,K02203) K01733",
        "(K00640,K23304) (K01738,K13034,K17069)",
        "K00455 K00151 K01826 K05921",
        "(K18072 K18073,K07644 K07665,K18297) K18093",
    ):
        echo(s)
    echo(
        "(K17755,((K00108,K11440,K00499) (K00130,K14085)))",
        "(K17755,(K00108,K11440,K00499) (K00130,K14085))",
    )
    echo(
        "K00826 ((K00166+K00167,K11381)+K09699+K00382) (K00253,K00249) (K01968+K01969) (K05607,K13766) K01640",
        "K00826 (K00166 K00167,K11381)+K09699+K00382 (K00253,K00249) K01968+K01969 (K05607,K13766) K01640",
    )
    echo("K09011 (K01703 K01704) K00052", "K09011 K01703+K01704 K00052")
    echo(
        "(K00765 K02502) ((K01523 K01496),K11755,K14152) (K01814,K24017) ((K02501 K02500),K01663) ((K01693 K00817 (K04486,K05602,K18649)),(K01089 K00817)) (K00013,K14152)",
        "K00765+K02502 (K01523 K01496,K11755,K14152) (K01814,K24017) (K02501 K02500,K01663) (K01693 K00817 (K04486,K05602,K18649),K01089 K00817) (K00013,K14152)",
    )


def test_kmodule_getitem():
    assert kmodule.KModule("K00058 K00831 (K01079,K02203,K22305)")["K00831"][0][1] == [
        "K00831"
    ]
    assert kmodule.KModule("K00058 K00831 (K01079,K02203,K22305)")["K00831"][1] == [
        1,
        0,
    ]
    assert kmodule.KModule("K00058 K00831 (K01079,K02203,K22305)")["K02079"] == (
        [],
        [-1],
    )

    e, i = kmodule.KModule(
        "K00826 ((K00166+K00167,K11381)+K09699+K00382) (K00253,K00249) (K01968+K01969) (K05607,K13766) K01640"
    )["K00382"]
    assert i == [1, 2, 0]
    assert e[1][2][0] == "K00382"
