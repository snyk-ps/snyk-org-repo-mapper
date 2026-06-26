"""Shared helpers for Stage 1 discovery file output."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from common.discovery_document import DiscoverySource, build_discovery_document, load_resume_rows
from common.empty_repos_document import default_empty_repos_filename, write_empty_repos_document
from common.mapper import row_is_empty
from common.output_state import atomic_write_json, completed_keys_from_rows, row_repo_key


def last_checkpoint_key(rows: list[dict[str, Any]]) -> tuple[str, str] | None:
    for row in reversed(rows):
        k = row_repo_key(row)
        if k is not None:
            return k
    return None


def resolve_empty_repos_path(
    *,
    output_path: str | None,
    empty_repos_output: str | None,
    no_empty_repos_output: bool,
    source: DiscoverySource = "bitbucket",
) -> Path | None:
    if no_empty_repos_output:
        return None
    if empty_repos_output is not None:
        return Path(empty_repos_output)
    if output_path:
        return Path(default_empty_repos_filename(source))
    return None


def flush_discovery(
    output_path: Path,
    rows: list[dict[str, Any]],
    *,
    source: DiscoverySource,
    empty_repos_path: Path | None,
) -> None:
    ck = last_checkpoint_key(rows)
    atomic_write_json(
        output_path,
        build_discovery_document(rows, source, last_completed=ck),
    )
    if empty_repos_path is not None:
        write_empty_repos_document(empty_repos_path, rows, source=source)


def log_empty_repo_summary(rows: list[dict[str, Any]], empty_repos_path: Path | None) -> None:
    n_empty = sum(1 for row in rows if row_is_empty(row))
    if empty_repos_path is not None:
        print(
            f"{n_empty} empty repositories (is_empty=true); see {empty_repos_path}",
            file=sys.stderr,
        )


def run_discovery_with_file_output(
    *,
    output_path: Path,
    row_iter_factory: Callable[[set[tuple[str, str]]], Iterator[dict[str, Any]]],
    flush_interval: int,
    empty_repos_path: Path | None,
    source: DiscoverySource = "bitbucket",
) -> None:
    """Incremental discovery with resume and periodic flush."""
    try:
        existing_rows = load_resume_rows(output_path)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    completed = completed_keys_from_rows(existing_rows)
    rows_accum: list[dict[str, Any]] = list(existing_rows)
    pending_flush = 0
    try:
        for row in row_iter_factory(completed):
            rows_accum.append(row)
            key = row_repo_key(row)
            if key is not None:
                completed.add(key)
            pending_flush += 1
            if pending_flush >= flush_interval:
                flush_discovery(
                    output_path,
                    rows_accum,
                    source=source,
                    empty_repos_path=empty_repos_path,
                )
                pending_flush = 0
    finally:
        flush_discovery(
            output_path,
            rows_accum,
            source=source,
            empty_repos_path=empty_repos_path,
        )
        log_empty_repo_summary(rows_accum, empty_repos_path)
