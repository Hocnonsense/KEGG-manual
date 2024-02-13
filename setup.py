# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-11 13:20:35
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-13 11:05:13
 * @FilePath: /KEGG/setup.py
 * @Description:
"""
# """

from pathlib import Path

repo_path = Path(__file__).parent


if __name__ == "__main__":
    import os
    from setuptools import setup, find_packages

    os.chdir(repo_path)
    setup(
        name="kegg_manual",
        version="0.0.1",
        author="hwrn.aou",
        author_email="hwrn.aou@sjtu.edu.cn",
        description="local handler of KEGG data",
        # 你要安装的包，通过 setuptools.find_packages 找到当前目录下有哪些包
        packages=find_packages(where=repo_path, exclude=[""]),
        include_package_data=True,
    )
