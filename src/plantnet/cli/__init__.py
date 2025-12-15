"""Command-line interface modules for PlantNet."""

from plantnet.cli.analysis_cmds import analyze_cli
from plantnet.cli.database_cmds import build_cli, query_cli
from plantnet.cli.image_cmds import deduplicate_cli, download_cli, embeddings_cli
from plantnet.cli.main import main

__all__ = [
    "main",
    "query_cli",
    "build_cli",
    "deduplicate_cli",
    "embeddings_cli",
    "download_cli",
    "analyze_cli",
]
