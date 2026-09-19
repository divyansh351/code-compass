"""Git history extractor for local repositories."""

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GitCommitInfo:
    """Represents a local Git commit metadata."""
    hexsha: str
    author_name: str
    author_email: str
    committed_datetime: str
    message: str
    files_changed: List[str] = field(default_factory=list)


@dataclass
class GitRepoSummary:
    """Summary of git status and history."""
    is_git_repo: bool
    current_branch: Optional[str] = None
    head_commit: Optional[str] = None
    commits: List[GitCommitInfo] = field(default_factory=list)


class GitExtractor:
    """Extracts local Git history and file modification logs using the git CLI."""

    def __init__(self, repo_path: Path | str):
        self.repo_path = Path(repo_path).resolve()
        self.git_available = shutil.which("git") is not None

    def is_git_repository(self) -> bool:
        """Check if directory is inside a git repository."""
        if not self.git_available:
            return False
        git_dir = self.repo_path / ".git"
        if git_dir.exists():
            return True
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.returncode == 0 and res.stdout.strip() == "true"
        except Exception:
            return False

    def extract_history(self, max_commits: int = 100) -> GitRepoSummary:
        """Extract recent commit history and modified file mappings."""
        if not self.is_git_repository():
            return GitRepoSummary(is_git_repo=False)

        try:
            # Get current branch
            branch_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            current_branch = branch_res.stdout.strip() if branch_res.returncode == 0 else None

            # Get commit log with custom format and list of changed files
            # Format: HASH%x1fAUTHOR_NAME%x1fAUTHOR_EMAIL%x1fDATE%x1fSUBJECT%x1e
            cmd = [
                "git",
                "log",
                f"-n{max_commits}",
                "--name-only",
                "--pretty=format:%H%x1f%an%x1f%ae%x1f%ad%x1f%s%x1e",
                "--date=iso",
            ]
            log_res = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=15,
            )

            if log_res.returncode != 0:
                return GitRepoSummary(is_git_repo=True, current_branch=current_branch)

            raw_entries = log_res.stdout.split("\x1e")
            commits: List[GitCommitInfo] = []

            for entry in raw_entries:
                entry = entry.strip()
                if not entry:
                    continue

                lines = entry.split("\n")
                header = lines[0].strip()
                changed_files = [f.strip().replace("\\", "/") for f in lines[1:] if f.strip()]

                fields = header.split("\x1f")
                if len(fields) >= 5:
                    commits.append(
                        GitCommitInfo(
                            hexsha=fields[0],
                            author_name=fields[1],
                            author_email=fields[2],
                            committed_datetime=fields[3],
                            message=fields[4],
                            files_changed=changed_files,
                        )
                    )

            head_commit = commits[0].hexsha if commits else None
            return GitRepoSummary(
                is_git_repo=True,
                current_branch=current_branch,
                head_commit=head_commit,
                commits=commits,
            )
        except Exception as e:
            logger.debug(f"Git extraction failed: {e}")
            return GitRepoSummary(is_git_repo=True)
