"""Document claim extraction and analysis."""

from __future__ import annotations

import re

from src.ingest.secure_loader import SecureLoader
from src.models import DocAnalysisResult, RedFlag, Severity


# Patterns for extracting specific types of claims
PERFORMANCE_CLAIM_PATTERNS = [
    r"\d+x\s+(faster|improvement|speedup|better)",
    r"\d+%\s+(faster|reduction|improvement|accuracy)",
    r"(sub-second|millisecond|real-time|instant)\s+(response|latency|processing)",
    r"(handles|processes|supports)\s+\d+[kKmMbB]?\+?\s+(requests|users|transactions)",
    r"\d+\.\d+%\s+accuracy",
]

ARCHITECTURE_CLAIM_PATTERNS = [
    r"(proprietary|custom|novel)\s+(algorithm|model|architecture|engine|framework)",
    r"(patent|patented|patent-pending)",
    r"(end-to-end|E2E)\s+(encrypted|encryption)",
    r"(zero-knowledge|homomorphic|federated)\s+(proof|encryption|learning)",
    r"(microservice|serverless|distributed)\s+architecture",
]

BUZZWORD_PATTERNS = [
    r"\b(revolutionary|groundbreaking|disruptive|paradigm.shift|world.class)\b",
    r"\b(AI.powered|AI.driven|AI.native|AI.first)\b",
    r"\b(blockchain|web3|metaverse|quantum)\b",
]


class DocAnalyzer:
    """Analyzes documentation and pitch materials for claims."""

    def __init__(self, loader: SecureLoader) -> None:
        self._loader = loader

    def analyze(self) -> DocAnalysisResult:
        """Extract and categorize claims from all documentation.

        Returns:
            DocAnalysisResult with categorized claims and red flags.
        """
        result = DocAnalysisResult()
        doc_files = self._loader.get_doc_files()

        for entry in doc_files:
            try:
                content = self._loader.read_file(entry["path"])
            except (FileNotFoundError, UnicodeDecodeError):
                continue

            self._extract_claims(content, entry["path"], result)

        self._generate_red_flags(result)
        return result

    def _extract_claims(
        self, content: str, path: str, result: DocAnalysisResult
    ) -> None:
        """Extract technical, performance, and architecture claims from text."""
        lines = content.splitlines()

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Performance claims
            for pattern in PERFORMANCE_CLAIM_PATTERNS:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    result.performance_claims.append(line_stripped)
                    result.claims.append({
                        "type": "performance",
                        "text": line_stripped,
                        "source": f"{path}:{i + 1}",
                    })

            # Architecture claims
            for pattern in ARCHITECTURE_CLAIM_PATTERNS:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    result.architecture_claims.append(line_stripped)
                    result.claims.append({
                        "type": "architecture",
                        "text": line_stripped,
                        "source": f"{path}:{i + 1}",
                    })

            # General technical claims (sentences with technical keywords)
            if _is_technical_claim(line_stripped):
                result.technical_claims.append(line_stripped)
                result.claims.append({
                    "type": "technical",
                    "text": line_stripped,
                    "source": f"{path}:{i + 1}",
                })

    def _generate_red_flags(self, result: DocAnalysisResult) -> None:
        """Generate red flags from document analysis."""
        # Excessive buzzwords
        all_text = " ".join(c["text"] for c in result.claims)
        buzzword_count = sum(
            len(re.findall(p, all_text, re.IGNORECASE))
            for p in BUZZWORD_PATTERNS
        )
        if buzzword_count > 10:
            result.red_flags.append(
                RedFlag(
                    category="documentation",
                    title="Excessive buzzword usage",
                    description=(
                        f"Found {buzzword_count} buzzword instances across documents. "
                        f"Heavy use of marketing language may obscure technical reality."
                    ),
                    severity=Severity.MEDIUM,
                    evidence=[all_text[:200]],
                )
            )

        # Unsubstantiated performance claims
        unquantified = [
            c for c in result.performance_claims
            if not re.search(r"\d", c)
        ]
        if len(unquantified) > 3:
            result.red_flags.append(
                RedFlag(
                    category="documentation",
                    title="Unquantified performance claims",
                    description=(
                        f"{len(unquantified)} performance claims lack specific numbers "
                        f"or benchmarks."
                    ),
                    severity=Severity.MEDIUM,
                    evidence=unquantified[:5],
                )
            )

        # Proprietary tech claims without evidence
        proprietary_claims = [
            c for c in result.architecture_claims
            if re.search(r"proprietary|custom|novel", c, re.IGNORECASE)
        ]
        if len(proprietary_claims) > 0:
            result.findings.append(
                f"Found {len(proprietary_claims)} proprietary technology claims "
                f"that should be verified against codebase."
            )

        # No documentation at all
        if len(result.claims) == 0:
            result.red_flags.append(
                RedFlag(
                    category="documentation",
                    title="No meaningful documentation",
                    description="No technical claims or documentation found to analyze.",
                    severity=Severity.HIGH,
                )
            )


def _is_technical_claim(text: str) -> bool:
    """Heuristic: determine if a line contains a technical claim."""
    technical_keywords = [
        "algorithm", "model", "architecture", "pipeline", "engine",
        "framework", "protocol", "encryption", "latency", "throughput",
        "scalable", "distributed", "real-time", "ml", "machine learning",
        "neural", "transformer", "inference", "training",
    ]
    text_lower = text.lower()
    keyword_hits = sum(1 for kw in technical_keywords if kw in text_lower)
    # Must have at least 2 keywords and be a reasonably long sentence
    return keyword_hits >= 2 and len(text) > 30
