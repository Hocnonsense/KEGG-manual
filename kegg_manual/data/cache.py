# -*- coding: utf-8 -*-
"""
 * @Date: 2024-02-13 10:58:21
 * @LastEditors: Hwrn hwrn.aou@sjtu.edu.cn
 * @LastEditTime: 2024-07-11 11:50:37
 * @FilePath: /KEGG/kegg_manual/data/cache.py
 * @Description:
"""
# """

import atexit
import datetime
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from typing import Callable, Literal, TextIO

import importlib_resources


db_kegg_manual_data = importlib_resources.files("kegg_manual.data")
db_kegg_manual_data_config = Path(f"{db_kegg_manual_data}.yaml")
db_kegg_manual_verbose = True


def data_config(config=db_kegg_manual_data_config):
    """
    read database config of KEGG database

    `dataconfig(<Path>):`
        read given config file
        missing values in config will be set by current settings
    `dataconfig() -> (<key> = <value>):`
        update settings:
            db_kegg_manual_data: Path
            db_kegg_manual_verbose: bool | Literal["true", "false"]
    `dataconfig()() -> (<Path>):`
        aply or write config to configfile
    """
    import yaml

    global db_kegg_manual_data, db_kegg_manual_verbose

    input_configfile = config
    if Path(input_configfile).is_file():
        with open(input_configfile) as fi:
            raw_config = yaml.safe_load(fi)
    else:
        raw_config = {}
    this_config = {
        "db_kegg_manual_data": str(db_kegg_manual_data),
        "db_kegg_manual_verbose": str(db_kegg_manual_verbose),
    }

    def _update(**kwargs):
        """
        params:
            db_kegg_manual_data: Path
            db_kegg_manual_verbose: bool | Literal["true", "false"]

        settings will apply to this package
        """
        nonlocal this_config
        global db_kegg_manual_data, db_kegg_manual_verbose
        this_config |= {
            "db_kegg_manual_data": str(
                kwargs.get("db_kegg_manual_data", this_config["db_kegg_manual_data"])
            ),
            "db_kegg_manual_verbose": str(
                kwargs.get(
                    "db_kegg_manual_verbose", this_config["db_kegg_manual_verbose"]
                )
            ).lower(),
        }
        db_kegg_manual_data = Path(this_config["db_kegg_manual_data"])
        db_kegg_manual_verbose = this_config["db_kegg_manual_verbose"] == "true"

        def _set(config=input_configfile):
            global db_kegg_manual_data, db_kegg_manual_verbose
            Path(config).parent.mkdir(parents=True, exist_ok=True)
            with open(config, "w") as fo:
                yaml.safe_dump(this_config, fo)
            return config

        return _set

    setattr(_update, "config", this_config)
    _update(**raw_config)

    return _update


data_config()()

changed_cached_files: dict[Path, tuple[str, Callable[[str], TextIO]]] = {}


@atexit.register
def report_updated_on_exit():
    if changed_cached_files:
        warnings.warn(
            "updated files:\n    "
            + ("\n    ".join(str(i) for i in changed_cached_files))
        )


@dataclass
class CachedModified:
    func_to_file: Callable[[str], str] = None  # type: ignore [assignment]
    func_to_file_modify: Callable[[Path], Path] | None = None
    keep_seconds = 15552000
    db: str | Path | None = None
    download_wait_s: int | float = 1

    def __post_init__(self) -> None:
        self.rset_get_io = staticmethod(
            file_cached(self.func_to_file, self.func_to_file_modify, self.keep_seconds)(
                self._get_io
            )
        )

    def _get_io(self, source: str) -> TextIO:
        sleep(self.download_wait_s)
        return  # type: ignore [return-value]

    def load_single_raw(
        self,
        source: str,
        db: str | Path | None | Literal[-1] = -1,
        download_wait_s=-1,
    ):
        self.check_source_valid(source)

        rset_get_io = file_cached(self.func_to_file, None, self.keep_seconds)(
            self._get_io
        )

        with rset_get_io(
            source,
            self.db if db == -1 else db,
            self.download_wait_s if download_wait_s == -1 else download_wait_s,
        ) as file:
            raw_module = self.load_single_from_io(file)

        return self.update_entry(source, raw_module)

    def load_single(self, source: str):
        self.check_source_valid(source)
        with self.rset_get_io(source, self.db, self.keep_seconds) as file:
            raw_module = self.load_single_from_io(file)

        return self.update_entry(source, raw_module)

    def load_single_from_io(self, file: TextIO):
        return

    def check_source_valid(self, source: str):
        return True

    def update_entry(
        self, source: str, raw_module: dict[str, list[str | tuple[str, list[str]]]]
    ):
        return raw_module


def file_cached(
    func_to_file: Callable[[str], str],
    func_to_file_modify: Callable[[Path], Path] | None = None,
    keep_seconds=15552000,
):
    """
    This decorator let function to cache the string output to a file, so do not need to get the string again

    After given time (default 180 days (180d * 24h * 60m * 60s)), file should be created again

        - if keep_seconds < 0, file will never be updated
        - if keep_seconds < -1, file will never be updated or downloaded

    If there is a modify version of function default generated text, will return the modified version

    If file is updated, will warn user

    params in decorated functions:
        source: str for undecoreated function
        db: database (file or directory)
        keep_seconds: do not update file if updated recently
    """
    default_keep_seconds = keep_seconds

    def dfunc(func: Callable[[str], TextIO]):
        def dparams(
            source: str,
            /,
            db: str | Path | None = None,
            keep_seconds: int | None = None,
        ):
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
                db_file = db_ / func_to_file(source)

            # file read case 1: cached, read it:
            _keep_seconds = (
                keep_seconds if keep_seconds is not None else default_keep_seconds
            )
            if db_file.is_file():
                if _keep_seconds < 0:
                    cache_action = "use"
                elif file_modified_before(db_file, _keep_seconds):
                    warnings.warn(
                        f"{source}: cached file {db_file} is out of date, will update"
                    )
                    cache_action = "update"
                else:
                    cache_action = "use"
            else:
                assert (
                    -1 <= _keep_seconds
                ), "you forced not to update the existing cache, but nothing cached"
                db_file.parent.mkdir(parents=True, exist_ok=True)
                cache_action = "create"

            # file read case 2: no cached, will write to filename
            if cache_action != "use":
                file_in: TextIO = func(source)
                updated = atom_update_file(file_in, db_file)
            if cache_action == "update" and updated:
                # modify case 1: file is changed compared to the last version
                assert (
                    db_file not in changed_cached_files
                ), "file is update twice, please check it"
                warnings.warn(
                    f"{source}: cached file {db_file} is updated, please check"
                )
                changed_cached_files[db_file] = source, func
            elif func_to_file_modify is not None:
                # modify case 2: file is modified via user in the last version
                db_file_modify = func_to_file_modify(db_file)
                if db_file_modify.is_file():
                    db_file = db_file_modify
            return open(db_file)

        return dparams

    return dfunc


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

        if not to_file.parent.is_dir():
            to_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tpmf_out, to_file)
    return updated
