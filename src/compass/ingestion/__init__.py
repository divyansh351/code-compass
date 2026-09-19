"""Ingestion module for Code Compass."""

from compass.ingestion.filesystem import FileScanner, ScanResult, ScannedFile
from compass.ingestion.git import GitCommitInfo, GitExtractor, GitRepoSummary
from compass.ingestion.repository import RepositoryData, RepositoryIngestor

__all__ = [
    "FileScanner",
    "ScanResult",
    "ScannedFile",
    "GitCommitInfo",
    "GitExtractor",
    "GitRepoSummary",
    "RepositoryData",
    "RepositoryIngestor",
]
