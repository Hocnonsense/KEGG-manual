# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-13 11:04:14
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-07-11 11:09:57
 * @FilePath: /KEGG/tests/__init__.py
 * @Description:
# python -m pytest  --cov-report=html --cov=kegg_manual -v
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable


test_temp = Path(__file__).parent / "temp"
test_files = Path(__file__).parent / "file"


def temp_output(f: Callable[[Path], None]):
    def _f():
        with TemporaryDirectory(prefix=str(test_temp)) as _td:
            f(Path(_td))

    return _f
