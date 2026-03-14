"""AST-based code analysis for detecting API wrappers and real implementation."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from src.ingest.secure_loader import SecureLoader
from src.models import CodeAnalysisResult, RedFlag, Severity


# Patterns that suggest thin API wrapping rather than real implementation
API_WRAPPER_PATTERNS = [
    r"openai\.",
    r"anthropic\.",
    r"requests\.(get|post|put|delete)\(",
    r"httpx\.(get|post|put|delete)\(",
    r"fetch\(",
    r"axios\.(get|post|put|delete)\(",
    r"\.completions\.create\(",
    r"\.chat\.completions\.",
    r"\.generate\(",
]

# Patterns indicating real algorithmic implementation
REAL_IMPL_PATTERNS = [
    r"class\s+\w+Model",
    r"def\s+(forward|backward|train_step|predict)\(",
    r"torch\.",
    r"tensorflow\.",
    r"numpy\.",
    r"sklearn\.",
    r"def\s+\w+algorithm\(",
]


class CodeAnalyzer:
    """Analyzes source code for quality, originality, and red flags."""

    def __init__(self, loader: SecureLoader) -> None:
        self._loader = loader

    def analyze(self) -> CodeAnalysisResult:
        """Run full code analysis across all code files.

        Returns:
            CodeAnalysisResult with metrics, findings, and red flags.
        """
        result = CodeAnalysisResult()
        code_files = self._loader.get_code_files()
        result.total_files = len(code_files)

        api_call_files = 0
        real_impl_files = 0

        for entry in code_files:
            path = entry["path"]
            suffix = Path(path).suffix
            result.languages[suffix] = result.languages.get(suffix, 0) + 1

            try:
                content = self._loader.read_file(path)
            except (FileNotFoundError, UnicodeDecodeError):
                continue

            lines = content.splitlines()
            result.total_lines += len(lines)

            # Check for API wrapper patterns
            has_api_calls = any(
                re.search(pattern, content) for pattern in API_WRAPPER_PATTERNS
            )
            has_real_impl = any(
                re.search(pattern, content) for pattern in REAL_IMPL_PATTERNS
            )

            if has_api_calls:
                api_call_files += 1
            if has_real_impl:
                real_impl_files += 1

            # Python-specific AST analysis
            if suffix == ".py":
                self._analyze_python_ast(path, content, result)

            # Check for test files
            if "test" in path.lower() or "spec" in path.lower():
                result.has_tests = True

        # Compute API wrapper ratio
        if result.total_files > 0:
            result.api_wrapper_ratio = api_call_files / result.total_files

        # Check for CI/CD
        result.has_ci_cd = self._check_ci_cd()

        # Check for documentation
        result.has_documentation = self._check_documentation()

        # Dependency analysis
        result.dependency_count = self._count_dependencies()

        # Generate red flags
        self._generate_red_flags(result, api_call_files, real_impl_files)

        return result

    def _analyze_python_ast(
        self, path: str, content: str, result: CodeAnalysisResult
    ) -> None:
        """Perform AST analysis on Python files."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            result.findings.append(f"Syntax error in {path}")
            return

        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        # Check function complexity (rough: count branches)
        for func in functions:
            branch_count = sum(
                1
                for node in ast.walk(func)
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler))
            )
            if branch_count > 15:
                result.findings.append(
                    f"High complexity ({branch_count} branches) in {path}:{func.name}"
                )

        # Check for empty classes (possible stubs)
        for cls in classes:
            body_stmts = [
                s for s in cls.body
                if not isinstance(s, (ast.Pass, ast.Expr))
                or (isinstance(s, ast.Expr) and not isinstance(s.value, ast.Constant))
            ]
            if len(body_stmts) == 0:
                result.findings.append(f"Empty class {cls.name} in {path} (possible stub)")

        # Detect functions that just call an API and return
        for func in functions:
            if len(func.body) <= 3:
                source_segment = ast.get_source_segment(content, func)
                if source_segment and any(
                    re.search(p, source_segment) for p in API_WRAPPER_PATTERNS
                ):
                    result.findings.append(
                        f"Thin API wrapper: {func.name} in {path}"
                    )

    def _check_ci_cd(self) -> bool:
        """Check if CI/CD configuration exists."""
        ci_indicators = [
            ".github/workflows",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
            "azure-pipelines.yml",
            ".travis.yml",
        ]
        for entry in self._loader.manifest:
            for indicator in ci_indicators:
                if indicator in entry["path"]:
                    return True
        return False

    def _check_documentation(self) -> bool:
        """Check if meaningful documentation exists."""
        doc_files = self._loader.get_doc_files()
        has_readme = any("readme" in f["path"].lower() for f in doc_files)
        has_docs_dir = any("docs/" in f["path"].lower() for f in doc_files)
        return has_readme or has_docs_dir

    def _count_dependencies(self) -> int:
        """Count project dependencies from manifest files."""
        dep_count = 0
        dep_files = [
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "Gemfile",
        ]
        for entry in self._loader.manifest:
            if any(entry["path"].endswith(df) for df in dep_files):
                try:
                    content = self._loader.read_file(entry["path"])
                    # Rough line count as proxy for dependency count
                    dep_count += sum(
                        1
                        for line in content.splitlines()
                        if line.strip()
                        and not line.strip().startswith("#")
                        and not line.strip().startswith("//")
                    )
                except (FileNotFoundError, UnicodeDecodeError):
                    pass
        return dep_count

    def _generate_red_flags(
        self,
        result: CodeAnalysisResult,
        api_call_files: int,
        real_impl_files: int,
    ) -> None:
        """Generate red flags based on analysis findings."""
        # High API wrapper ratio
        if result.api_wrapper_ratio > 0.5 and result.total_files > 5:
            result.red_flags.append(
                RedFlag(
                    category="code_originality",
                    title="High API wrapper ratio",
                    description=(
                        f"{result.api_wrapper_ratio:.0%} of code files contain API "
                        f"calls with minimal custom logic. This suggests the product "
                        f"may be a thin wrapper around third-party APIs."
                    ),
                    severity=Severity.HIGH,
                    evidence=[
                        f"{api_call_files} files with API calls",
                        f"{real_impl_files} files with real implementation patterns",
                    ],
                )
            )

        # No tests
        if not result.has_tests and result.total_files > 10:
            result.red_flags.append(
                RedFlag(
                    category="code_quality",
                    title="No test suite detected",
                    description="No test files found in the repository.",
                    severity=Severity.MEDIUM,
                )
            )

        # No CI/CD
        if not result.has_ci_cd and result.total_files > 10:
            result.red_flags.append(
                RedFlag(
                    category="engineering_maturity",
                    title="No CI/CD pipeline",
                    description="No continuous integration configuration detected.",
                    severity=Severity.MEDIUM,
                )
            )

        # Very small codebase claiming to be a full product
        if result.total_lines < 500 and result.total_files > 0:
            result.red_flags.append(
                RedFlag(
                    category="code_substance",
                    title="Minimal codebase",
                    description=(
                        f"Only {result.total_lines} lines across {result.total_files} files. "
                        f"This is unusually small for a production product."
                    ),
                    severity=Severity.HIGH,
                )
            )
