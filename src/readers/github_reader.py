"""GitHub repository reader — clones repos from GitHub URLs.

Enables cloud deployment (HF Spaces, Railway, etc.) where users
can't provide local filesystem paths. Instead they paste a GitHub
URL and this module handles cloning, caching, and cleanup.
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# Default cache directory for cloned repos
DEFAULT_CACHE_DIR = "/tmp/neo-tdg-repos"


class GitHubReader:
    """Clone and manage GitHub repositories for source code analysis."""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── URL Parsing ───────────────────────────────────────────────────────

    @staticmethod
    def is_github_url(text: str) -> bool:
        """Check if the given text looks like a GitHub URL."""
        if not text:
            return False
        text = text.strip()
        return bool(
            re.match(
                r"^https?://(www\.)?github\.com/[\w.\-]+/[\w.\-]+",
                text,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def parse_github_url(url: str) -> Tuple[str, str, Optional[str]]:
        """Parse a GitHub URL into (owner, repo, branch).

        Supports formats:
          - https://github.com/owner/repo
          - https://github.com/owner/repo.git
          - https://github.com/owner/repo/tree/branch-name
          - https://github.com/owner/repo/tree/branch/sub/path

        Returns:
            Tuple of (owner, repo_name, branch_or_none)
        """
        url = url.strip().rstrip("/")

        # Remove .git suffix if present
        url = re.sub(r"\.git$", "", url)

        match = re.match(
            r"https?://(?:www\.)?github\.com/([\w.\-]+)/([\w.\-]+)(?:/tree/([\w.\-/]+))?",
            url,
            re.IGNORECASE,
        )
        if not match:
            raise ValueError(
                f"Invalid GitHub URL: {url}\n"
                "Expected: https://github.com/owner/repo"
            )

        owner = match.group(1)
        repo = match.group(2)
        branch_path = match.group(3)

        # Extract just the branch name (first path segment after /tree/)
        branch = None
        if branch_path:
            branch = branch_path.split("/")[0]

        return owner, repo, branch

    # ── Clone Operations ──────────────────────────────────────────────────

    def clone(
        self,
        url: str,
        branch: Optional[str] = None,
        shallow: bool = True,
        progress_callback=None,
    ) -> str:
        """Clone a GitHub repository to the local cache.

        Args:
            url: GitHub repository URL
            branch: Branch to clone (default: repo's default branch)
            shallow: Use shallow clone (--depth 1) for speed
            progress_callback: Optional callback(status_message: str)

        Returns:
            Local filesystem path to the cloned repository
        """
        owner, repo, url_branch = self.parse_github_url(url)

        # Use branch from URL if not explicitly provided
        if not branch and url_branch:
            branch = url_branch

        # Build clone URL (always use HTTPS for public repos)
        clone_url = f"https://github.com/{owner}/{repo}.git"

        # Target directory
        dir_name = f"{owner}__{repo}"
        if branch:
            dir_name += f"__{branch}"
        target_dir = self.cache_dir / dir_name

        # If already cloned, pull latest
        if target_dir.exists() and (target_dir / ".git").exists():
            logger.info(f"Repository already cached at {target_dir}, pulling latest...")
            if progress_callback:
                progress_callback(f"Updating cached repo {owner}/{repo}...")

            try:
                subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=str(target_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                logger.info(f"Updated {owner}/{repo}")
                return str(target_dir)
            except Exception as e:
                logger.warning(f"Pull failed, re-cloning: {e}")
                shutil.rmtree(target_dir, ignore_errors=True)

        # Fresh clone
        if progress_callback:
            progress_callback(f"Cloning {owner}/{repo}...")

        cmd = ["git", "clone"]

        if shallow:
            cmd.extend(["--depth", "1"])

        if branch:
            cmd.extend(["--branch", branch])

        cmd.extend([clone_url, str(target_dir)])

        logger.info(f"Cloning: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5-minute timeout for large repos
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                # Common error: branch not found
                if "not found" in error_msg.lower() or "could not find" in error_msg.lower():
                    raise ValueError(
                        f"Branch '{branch}' not found in {owner}/{repo}. "
                        f"Check the branch name and try again."
                    )
                raise RuntimeError(
                    f"Git clone failed (exit {result.returncode}): {error_msg}"
                )

            if progress_callback:
                progress_callback(f"Successfully cloned {owner}/{repo}")

            logger.info(f"Cloned {owner}/{repo} to {target_dir}")
            return str(target_dir)

        except subprocess.TimeoutExpired:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise RuntimeError(
                f"Clone timed out after 5 minutes. "
                f"The repository {owner}/{repo} may be too large."
            )

    # ── File Discovery ────────────────────────────────────────────────────

    @staticmethod
    def find_solution_files(repo_path: str) -> List[str]:
        """Find all .sln files in a cloned repository.

        Returns:
            List of absolute paths to .sln files
        """
        repo = Path(repo_path)
        sln_files = sorted(repo.rglob("*.sln"))
        # Exclude common non-project directories
        excluded = {"node_modules", ".git", "bin", "obj", "packages"}
        return [
            str(f)
            for f in sln_files
            if not any(part in excluded for part in f.parts)
        ]

    @staticmethod
    def find_markdown_files(repo_path: str) -> List[str]:
        """Find all markdown files in a cloned repository.

        Returns:
            List of absolute paths to .md files
        """
        repo = Path(repo_path)
        md_files = sorted(repo.rglob("*.md"))
        excluded = {"node_modules", ".git", "bin", "obj", "packages"}
        return [
            str(f)
            for f in md_files
            if not any(part in excluded for part in f.parts)
        ]

    @staticmethod
    def find_source_files(repo_path: str) -> List[str]:
        """Find all source code files in a cloned repository.

        Returns:
            List of absolute paths to source files (.cs, .py, .js, .ts, .java, etc.)
        """
        repo = Path(repo_path)
        extensions = {
            ".cs", ".py", ".js", ".ts", ".tsx", ".jsx",
            ".java", ".go", ".rs", ".rb", ".php",
            ".c", ".cpp", ".h", ".hpp",
            ".yaml", ".yml", ".json", ".xml", ".toml",
        }
        excluded = {"node_modules", ".git", "bin", "obj", "packages", "dist", "build", "__pycache__"}
        source_files = []
        for f in repo.rglob("*"):
            if f.is_file() and f.suffix.lower() in extensions:
                if not any(part in excluded for part in f.parts):
                    source_files.append(str(f))
        return sorted(source_files)

    @staticmethod
    def get_repo_summary(repo_path: str) -> dict:
        """Get a quick summary of a cloned repository.

        Returns:
            Dict with file counts by extension, total files, etc.
        """
        repo = Path(repo_path)
        excluded = {"node_modules", ".git", "bin", "obj", "packages", "dist", "build", "__pycache__"}

        ext_counts = {}
        total_files = 0

        for f in repo.rglob("*"):
            if f.is_file() and not any(part in excluded for part in f.parts):
                total_files += 1
                ext = f.suffix.lower() or "(no ext)"
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        # Sort by count descending
        ext_counts = dict(sorted(ext_counts.items(), key=lambda x: -x[1]))

        return {
            "total_files": total_files,
            "extensions": ext_counts,
            "sln_count": len(GitHubReader.find_solution_files(repo_path)),
            "md_count": len(GitHubReader.find_markdown_files(repo_path)),
        }

    # ── Cleanup ───────────────────────────────────────────────────────────

    def cleanup(self, repo_path: str) -> None:
        """Remove a cloned repository from the cache."""
        path = Path(repo_path)
        if path.exists() and str(path).startswith(str(self.cache_dir)):
            shutil.rmtree(path, ignore_errors=True)
            logger.info(f"Cleaned up: {path}")

    def cleanup_all(self) -> None:
        """Remove all cached repositories."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cleaned up all cached repos")

    def get_cached_repos(self) -> List[str]:
        """List all currently cached repository directories."""
        if not self.cache_dir.exists():
            return []
        return [
            str(d)
            for d in self.cache_dir.iterdir()
            if d.is_dir() and (d / ".git").exists()
        ]
