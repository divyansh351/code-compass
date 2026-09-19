"""Repository scanning orchestrator."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from compass.config.settings import CompassConfig
from compass.ingestion.filesystem import FileScanner, ScanResult, ScannedFile
from compass.ingestion.git import GitExtractor, GitRepoSummary


@dataclass
class RepositoryData:
    """Consolidated ingestion data for a repository."""
    root_path: Path
    scan_result: ScanResult
    git_summary: GitRepoSummary

    @property
    def files(self) -> List[ScannedFile]:
        return self.scan_result.files

    def get_files_by_language(self, language: str) -> List[ScannedFile]:
        return [f for f in self.scan_result.files if f.language == language]


class RepositoryIngestor:
    """Coordinates filesystem and VCS ingestion according to configuration."""

    def __init__(self, config: CompassConfig):
        self.config = config
        self.source_path = Path(config.source.path).resolve()
        self.scanner = FileScanner(
            root_path=self.source_path,
            ignore_patterns=config.source.ignore_patterns,
        )
        self.git_extractor = GitExtractor(repo_path=self.source_path)

    def ingest(self) -> RepositoryData:
        """Scan files and retrieve git history if enabled."""
        scan_result = self.scanner.scan()

        if self.config.analysis.git_history:
            git_summary = self.git_extractor.extract_history(
                max_commits=self.config.analysis.max_git_commits
            )
        else:
            git_summary = GitRepoSummary(is_git_repo=False)

        return RepositoryData(
            root_path=self.source_path,
            scan_result=scan_result,
            git_summary=git_summary,
        )
