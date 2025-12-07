# -*- coding: utf-8 -*-
"""
* @Date: 2024-02-13 10:58:21
* @LastEditors: hwrn hwrn.aou@sjtu.edu.cn
* @LastEditTime: 2025-12-07 10:08:03
* @FilePath: /KEGG-manual/kegg_manual/data/cache.py
* @Description:
"""
# """

import atexit
import datetime
import shutil
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from typing import Callable, Literal, TextIO

from importlib.resources import files


_db_kegg_manual_data = files("kegg_manual.data")


class ManualDataConfig:
    def __init__(self, configfile: str | Path = f"{_db_kegg_manual_data}.yaml"):
        self.configfile = Path(configfile)
        if self.configfile.is_file():
            import yaml

            with open(self.configfile) as fi:
                self.config = yaml.safe_load(fi)
        else:
            self.config = {}
        self.update(
            **{
                "db_kegg_manual_data": _db_kegg_manual_data,
                "db_kegg_manual_verbose": False,
            }
            | self.config
        )

    def update(self, **kwargs):
        """
        params:
            db_kegg_manual_data: Path
            db_kegg_manual_verbose: bool | Literal["true", "false"]

        settings will apply to this package
        """
        if "db_kegg_manual_data" in kwargs:
            self.database = Path(kwargs["db_kegg_manual_data"])
            self.config["db_kegg_manual_data"] = str(self.database)
        if "db_kegg_manual_verbose" in kwargs:
            self.config["db_kegg_manual_verbose"] = str(
                kwargs["db_kegg_manual_verbose"]
            ).lower()
            self.verbose = self.config["db_kegg_manual_verbose"] == "true"
        return self

    def save(self, configfile: str | Path | None = None):
        """
        write config to file
        """
        import yaml

        if configfile is not None:
            self.configfile = Path(configfile)
        self.configfile.parent.mkdir(parents=True, exist_ok=True)
        with open(self.configfile, "w") as fo:
            yaml.safe_dump(self.config, fo)
        return self.configfile

    def __call__(self, **kwargs):
        self.update(**kwargs)
        return self.save

    def copy(self):
        """
        return a copy of this config
        """
        return ManualDataConfig(self.configfile).update(**self.config)


manual_config = ManualDataConfig()


changed_cached_files: dict[Path, tuple[str, Callable[[str], TextIO]]] = {}


@atexit.register
def report_updated_on_exit(io_out=sys.stderr):
    if changed_cached_files:
        if io_out is sys.stderr:
            warnings.warn(
                "updated files:\n    "
                + ("\n    ".join(str(i) for i in changed_cached_files)),
                stacklevel=2,
            )
        else:
            for k, (v1, _v2) in changed_cached_files.items():
                print(k, v1, sep="\t", file=io_out)


@dataclass
class CachedModified:
    func_to_file_modify: Callable[[Path], Path] | None = None
    keep_seconds = 15552000
    db: str | Path | None = None
    # do not query too quickly.
    # -1: do not download file again, >=0: seconds to wait for
    download_wait_s: int | float = 1

    def func_to_file(self, source: str) -> str:
        return ""

    def redirect_modify(self, file: Path) -> Path:
        return file.parent.parent / "manual" / file.parent.name / file.name

    @staticmethod
    def outdated_name(file: Path):
        # last_modified = datetime.datetime.fromtimestamp(file.stat().st_mtime)
        now = datetime.datetime.now()
        return file.with_name(f"{file.name}.outdated.{now.strftime('%Y%m%d')}")

    def __post_init__(self) -> None:
        pass

    def sleep(self):
        sleep(self.download_wait_s)

    def rsync_io(self, source: str) -> TextIO:
        self.sleep()
        raise NotImplementedError

    def load_raw(
        self, source: str, db: str | Path | None | Literal[-1] = -1, keep_seconds=-1
    ):
        self.check_source_valid(source)
        with self.cache_io(
            source,
            self.db if db == -1 else db,
            self.keep_seconds if keep_seconds == -1 else keep_seconds,
            modify=False,
        ) as file:
            raw_module = self.parse_io(file)

        return self.update_entry(source, raw_module)

    def load(self, source: str):
        self.check_source_valid(source)
        with self.cache_io(source, self.db, self.keep_seconds) as file:
            raw_module = self.parse_io(file)

        return self.update_entry(source, raw_module)

    def parse_io(self, io_in: TextIO):
        raise NotImplementedError

    def check_source_valid(self, source: str):
        return True

    def update_entry(self, source: str, raw_module):
        return raw_module

    def cache_io(
        self,
        source: str,
        /,
        db: str | Path | None = None,
        keep_seconds: float = 1,
        modify=True,
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

        # db detect case 0: source is a file: string should not be affected by file on the dir
        # db detect case 1: filename not given:
        if not db:
            return self.rsync_io(source)
        # db detect case 2: use file as cache:
        db_ = Path(db)
        db_file = db_ if db_.is_file() else db_ / self.func_to_file(source)
        outdated_name = self.outdated_name(db_file)
        action = get_cache_file(
            self.rsync_io,
            source=source,
            db_file=db_file,
            keep_seconds=keep_seconds,
            outdated_name=outdated_name,
            verbose=manual_config.verbose,
        )
        if modify and self.func_to_file_modify is not None:
            # modify case 2: file is modified via user in the last version
            db_file_modify = self.func_to_file_modify(db_file)
            if db_file_modify.is_file():
                db_file = db_file_modify
        return open(db_file)


def decide_file_action(db_file: Path, source: str, keep_seconds: float):
    # file read case 1: cached, read it:
    if db_file.is_file():
        if keep_seconds < 0:
            cache_action = "use"
        elif file_modified_before(db_file, keep_seconds):
            warnings.warn(
                f"{source}: cached file {db_file} is out of date, will update",
                stacklevel=2,
            )
            cache_action = "update"
        else:
            cache_action = "use"
    else:
        assert (
            -1 <= keep_seconds
        ), "you forced not to update the existing cache, but nothing cached"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        cache_action = "create"
    return cache_action


def get_cache_file(
    rsync_io: Callable[[str], TextIO],
    source: str,
    db_file: Path,
    keep_seconds: float,
    outdated_name: Path | str = "",
    verbose: bool = False,
):
    cache_action = decide_file_action(db_file, source, keep_seconds)
    # file read case 2: no cached, will write to filename
    if cache_action != "use":
        file_in: TextIO = rsync_io(source)
        updated = atom_update_file(file_in, db_file, outdated_name)
    if cache_action == "update" and updated:
        # modify case 1: file is changed compared to the last version
        assert (
            db_file not in changed_cached_files
        ), "file is update twice, please check it"
        if verbose:
            warnings.warn(
                f"{source}: cached file {db_file} is updated, please check",
                stacklevel=2,
            )
        changed_cached_files[db_file] = source, rsync_io
    return cache_action


def file_modified_before(file: Path, seconds: float):
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


def atom_update_file(text: TextIO, to_file: Path, outdated_name: Path | str = ""):
    with NamedTemporaryFile("w", suffix="", delete=True) as tmpf:
        tpmf_out = Path(f"{tmpf.name}.shadow")
        with open(tpmf_out, "w") as fo:
            fo.write(text.read())

        updated = is_same_content(tpmf_out, to_file)

        if not to_file.parent.is_dir():
            to_file.parent.mkdir(parents=True, exist_ok=True)
        if updated and outdated_name and to_file.exists():
            to_file.rename(outdated_name)
        shutil.move(tpmf_out, to_file)
    return updated
