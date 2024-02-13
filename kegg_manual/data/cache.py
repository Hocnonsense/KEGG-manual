# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-13 10:58:21
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-02-13 11:02:06
 * @FilePath: /KEGG/kegg_manual/data/cache.py
 * @Description:
"""
# """

import datetime
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable, TextIO
import warnings
import atexit


changed_cached_files: dict[Path, tuple[str, Callable[[str], TextIO]]] = {}


@atexit.register
def report_updated_on_exit():
    if changed_cached_files:
        warnings.warn(
            "updated files:\n    "
            + ("\n    ".join(str(i) for i in changed_cached_files))
        )


def file_cached(
    func: Callable[[str], TextIO],
    func_to_file: Callable[[str], str],
    func_to_file_modify: Callable[[Path], Path] | None = None,
    keep_seconds=15552000,
):
    """
    This decorator let function to cache the string output to a file, so do not need to get the string again

    After given time (default 180 days (180d * 24h * 60m * 60s)), file should be created again

    If there is a modify version of function default generated text, will return the modified version

    If file is updated, will warn user
    """
    _keep_seconds = keep_seconds

    def decorator(
        source: str, /, db: str | Path | None = None, keep_seconds: int | None = None
    ):
        _keep_seconds = keep_seconds if keep_seconds is not None else _keep_seconds

        # db detect case 0: source is a file: string should not be affected by file on the dir
        # db detect case 1: filename not given:
        if not db:
            return func(source)

        # db detect case 2: use file as cache:
        db_ = Path(db)
        if db_.is_file():
            # db detect case 2.1: db is a file:
            db_file = db_
        else:
            # db detect case 2.1: db is not a file:
            db_.mkdir(parents=True, exist_ok=True)
            db_file = db_ / func_to_file(source)

        # file read case 1: cached, read it:
        if db_file.is_file():
            if file_modified_before(db_file, _keep_seconds):
                warnings.warn(
                    f"{source}: cached file {db_file} is out of date, will update"
                )
            else:
                return open(db_)

        # file read case 2: no cached, will write to filename
        file_in: TextIO = func(source)
        updated = atom_update_file(file_in, db_file)
        if updated:
            # modify case 1: file is changed compared to the last version
            assert (
                db_file not in changed_cached_files
            ), "file is update twice, please check it"
            warnings.warn(f"{source}: cached file {db_file} is updated, please check")
            changed_cached_files[db_file] = source, func
        elif func_to_file_modify is not None:
            # modify case 2: file is modified via user in the last version
            db_file_modify = func_to_file_modify(db_file)
            if db_file_modify.is_file():
                db_file = db_file_modify
        return open(db_file)

    return decorator


def file_modified_before(file: Path, seconds: int):
    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
    total_seconds = (datetime.datetime.now() - mtime).total_seconds()
    return seconds < total_seconds


def is_same_content(file1: Path | str, file2: Path | str):
    if not (Path(file1).is_file() and Path(file2).is_file()):
        return True
    with open(file1) as f1, open(file2) as f2:
        if any((l1 != l2 for l1, l2 in zip(f1, f2))):
            return True
        # assert nothing left
        return f1.read() != f2.read()


def atom_update_file(text: TextIO, to_file: Path):
    with NamedTemporaryFile("w", suffix="", delete=True) as tmpf:
        tpmf_out = Path(f"{tmpf.name}.shadow")
        with open(tpmf_out, "w") as fo:
            fo.write(text.read())

        updated = is_same_content(tpmf_out, to_file)

        shutil.move(tpmf_out, to_file)
    return updated
