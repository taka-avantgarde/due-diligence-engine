"""Git history analysis for detecting rush commits, fake history, and patterns."""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.models import GitForensicsResult, RedFlag, Severity


class GitForensicsAnalyzer:
    """Analyzes git repository history for suspicious patterns."""

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    def analyze(self) -> GitForensicsResult:
        """Run full git forensics analysis.

        Returns:
            GitForensicsResult with commit patterns and red flags.
        """
        result = GitForensicsResult()

        if not (self._repo_path / ".git").exists():
            result.findings.append("No .git directory found.")
            result.red_flags.append(
                RedFlag(
                    category="git",
                    title="No git history",
                    description=(
                        "Repository has no git history. Cannot verify development timeline."
                    ),
                    severity=Severity.HIGH,
                )
            )
            return result

        commits = self._get_commit_log()
        if not commits:
            result.findings.append("Empty git history.")
            return result

        result.total_commits = len(commits)
        authors = set()
        dates: list[datetime] = []
        hour_counter: Counter[int] = Counter()
        day_counter: Counter[str] = Counter()
        message_lengths: list[int] = []

        for commit in commits:
            authors.add(commit["author"])
            dt = commit["date"]
            dates.append(dt)
            hour_counter[dt.hour] += 1
            day_counter[dt.strftime("%A")] += 1
            message_lengths.append(len(commit["message"]))

        result.unique_authors = len(authors)
        result.first_commit_date = min(dates).isoformat() if dates else None
        result.last_commit_date = max(dates).isoformat() if dates else None
        result.commit_frequency = {str(k): v for k, v in sorted(hour_counter.items())}

        # Analyze patterns
        self._detect_rush_commits(commits, dates, result)
        self._detect_fake_history(commits, dates, result)
        self._detect_suspicious_messages(commits, message_lengths, result)
        self._detect_single_author_risk(result)

        return result

    def _get_commit_log(self) -> list[dict]:
        """Parse git log into structured commit data."""
        try:
            output = subprocess.run(
                [
                    "git", "log", "--format=%H|%an|%ae|%aI|%s",
                    "--no-merges",
                ],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if output.returncode != 0:
            return []

        commits = []
        for line in output.stdout.strip().splitlines():
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            try:
                dt = datetime.fromisoformat(parts[3])
            except ValueError:
                continue
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "email": parts[2],
                "date": dt,
                "message": parts[4],
            })
        return commits

    def _detect_rush_commits(
        self,
        commits: list[dict],
        dates: list[datetime],
        result: GitForensicsResult,
    ) -> None:
        """Detect unusually dense commit clusters suggesting last-minute work."""
        if len(dates) < 5:
            return

        # Sort dates and find clusters
        sorted_dates = sorted(dates)
        rush_windows: list[tuple[datetime, datetime, int]] = []

        # Sliding window: find 24-hour windows with high commit density
        for i, start in enumerate(sorted_dates):
            window_end = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
            count = 0
            for j in range(i, len(sorted_dates)):
                d = sorted_dates[j]
                d_aware = d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
                delta = (d_aware - window_end).total_seconds()
                if delta <= 86400:  # 24 hours
                    count += 1
                else:
                    break
            if count >= 20:  # More than 20 commits in 24h is suspicious
                rush_windows.append((start, sorted_dates[min(i + count - 1, len(sorted_dates) - 1)], count))

        if rush_windows:
            result.rush_commit_ratio = len(rush_windows) / max(len(dates), 1)
            result.suspicious_patterns.append(
                f"Found {len(rush_windows)} rush commit window(s) with 20+ commits in 24h"
            )
            result.red_flags.append(
                RedFlag(
                    category="git",
                    title="Rush commit pattern detected",
                    description=(
                        f"Detected {len(rush_windows)} time windows with extremely dense "
                        f"commit activity (20+ commits in 24 hours), suggesting last-minute "
                        f"cramming or artificial history creation."
                    ),
                    severity=Severity.HIGH,
                    evidence=[
                        f"{w[0].isoformat()} - {w[1].isoformat()}: {w[2]} commits"
                        for w in rush_windows[:5]
                    ],
                )
            )

    def _detect_fake_history(
        self,
        commits: list[dict],
        dates: list[datetime],
        result: GitForensicsResult,
    ) -> None:
        """Detect signs of fabricated git history."""
        if len(commits) < 2:
            return

        # Check for perfectly uniform commit intervals (bot-like)
        sorted_dates = sorted(dates)
        intervals = []
        for i in range(1, len(sorted_dates)):
            d1 = sorted_dates[i - 1]
            d2 = sorted_dates[i]
            d1_aware = d1.replace(tzinfo=timezone.utc) if d1.tzinfo is None else d1
            d2_aware = d2.replace(tzinfo=timezone.utc) if d2.tzinfo is None else d2
            intervals.append((d2_aware - d1_aware).total_seconds())

        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval > 0:
                variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
                cv = (variance ** 0.5) / avg_interval if avg_interval > 0 else 0

                if cv < 0.1 and len(intervals) > 20:
                    result.suspicious_patterns.append(
                        "Suspiciously uniform commit intervals (possible automated/fake history)"
                    )
                    result.red_flags.append(
                        RedFlag(
                            category="git",
                            title="Suspiciously uniform commit intervals",
                            description=(
                                f"Commit interval coefficient of variation is {cv:.3f} "
                                f"(near-zero variance). Natural development has irregular "
                                f"commit patterns."
                            ),
                            severity=Severity.CRITICAL,
                        )
                    )

        # Check for backdated commits (author date far from commit date)
        # This requires additional git log format
        self._check_date_tampering(result)

    def _check_date_tampering(self, result: GitForensicsResult) -> None:
        """Check if author dates differ significantly from commit dates."""
        try:
            output = subprocess.run(
                ["git", "log", "--format=%aI|%cI", "--no-merges"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return

        if output.returncode != 0:
            return

        tampered_count = 0
        for line in output.stdout.strip().splitlines():
            parts = line.split("|")
            if len(parts) != 2:
                continue
            try:
                author_date = datetime.fromisoformat(parts[0])
                commit_date = datetime.fromisoformat(parts[1])
                a = author_date.replace(tzinfo=timezone.utc) if author_date.tzinfo is None else author_date
                c = commit_date.replace(tzinfo=timezone.utc) if commit_date.tzinfo is None else commit_date
                diff_hours = abs((a - c).total_seconds()) / 3600
                if diff_hours > 24:
                    tampered_count += 1
            except ValueError:
                continue

        if tampered_count > 5:
            result.red_flags.append(
                RedFlag(
                    category="git",
                    title="Possible date tampering",
                    description=(
                        f"{tampered_count} commits have author dates differing from "
                        f"commit dates by more than 24 hours, suggesting history rewriting."
                    ),
                    severity=Severity.HIGH,
                    evidence=[f"{tampered_count} commits with date discrepancies"],
                )
            )

    def _detect_suspicious_messages(
        self,
        commits: list[dict],
        message_lengths: list[int],
        result: GitForensicsResult,
    ) -> None:
        """Detect suspicious commit message patterns."""
        # Check for generic/placeholder messages
        generic_patterns = [
            r"^(update|fix|change|commit|wip|tmp|test|asdf|xxx)$",
            r"^initial commit$",
            r"^\.+$",
        ]
        generic_count = sum(
            1
            for c in commits
            if any(re.match(p, c["message"].strip(), re.IGNORECASE) for p in generic_patterns)
        )

        if generic_count > len(commits) * 0.5 and len(commits) > 10:
            result.red_flags.append(
                RedFlag(
                    category="git",
                    title="Low-quality commit messages",
                    description=(
                        f"{generic_count}/{len(commits)} commits have generic or "
                        f"meaningless messages, indicating poor development practices."
                    ),
                    severity=Severity.LOW,
                )
            )

    def _detect_single_author_risk(self, result: GitForensicsResult) -> None:
        """Flag bus-factor risk from single-author repositories."""
        if result.unique_authors == 1 and result.total_commits > 50:
            result.red_flags.append(
                RedFlag(
                    category="team",
                    title="Single-author repository",
                    description=(
                        f"All {result.total_commits} commits are from a single author. "
                        f"This represents a significant bus-factor risk."
                    ),
                    severity=Severity.MEDIUM,
                )
            )
