"""IDE AI向け構造化プロンプト生成モジュール。

DDE のヒューリスティック分析結果を、IDE 内 AI（Claude Code, Cursor 等）が
理解・評価できる構造化プロンプトとして出力する。

特徴:
- 非IT業界の利用者向けに全技術用語に注釈を付与（ほんやくコンニャク方式）
- 6次元スコアリング + ステータスバー表示 (100点満点)
- 強み・弱みの詳細分析と「何ができるようになるか」の事例説明
- 「こうすればもっと良くなる」改善提案
- サービスサイトURL貼り付けによる主張vs実態の乖離分析を促進
- マッチ率（主張と実装の一致度）表示
- 投資家向け質問リストの自動生成
"""

from __future__ import annotations

import json
from typing import Any

from src.models import AnalysisResult, RedFlag


# ---------------------------------------------------------------------------
# 用語集（Glossary）: IT業界外の読者向け
# ---------------------------------------------------------------------------

GLOSSARY_EN = {
    "API wrapper ratio": (
        "The percentage of code that merely calls external services (e.g. OpenAI, AWS) "
        "rather than implementing its own logic. A high ratio means the product has "
        "little original technology — like a restaurant that only reheats frozen meals."
    ),
    "CI/CD": (
        "Continuous Integration / Continuous Delivery — an automated system that tests "
        "and deploys code every time a developer makes a change. Think of it as a "
        "factory's quality control line. Without CI/CD, quality depends entirely on "
        "manual checks."
    ),
    "Rush commits": (
        "A burst of 20+ code changes within 24 hours. This may indicate deadline panic, "
        "but in AI-assisted development (Claude Code, Cursor) it's normal — like a chef "
        "using a food processor instead of chopping by hand."
    ),
    "Dependency count": (
        "The number of external software libraries the project relies on. Like ingredients "
        "in a recipe — more ingredients mean more things that could go wrong, but also "
        "richer functionality."
    ),
    "Consistency score": (
        "How well the project's documentation claims match the actual code. Like comparing "
        "a restaurant's menu description with what actually arrives on your plate."
    ),
    "Red flag": (
        "A warning sign found during analysis. Like a health inspector's report — ranges from "
        "INFO (minor note) to CRITICAL (potential deal-breaker)."
    ),
    "Git forensics": (
        "Analysis of the project's version control history — who wrote what, when, "
        "and how often. Like reviewing a building's construction log to see "
        "if it was built carefully or rushed."
    ),
    "Test coverage": (
        "The percentage of code that has automated tests. Like a car manufacturer "
        "testing each component — higher coverage means fewer hidden defects."
    ),
    "Monorepo": (
        "A single code repository containing multiple projects (e.g. frontend + backend + "
        "mobile app). Like a department store vs. separate shops — dependency counts "
        "are naturally higher."
    ),
    "Technical debt": (
        "Shortcuts taken during development that will need to be fixed later. Like "
        "building a house quickly with temporary materials — it works now, but "
        "maintenance costs increase over time."
    ),
    "E2EE": (
        "End-to-End Encryption — messages encrypted on the sender's device, "
        "decryptable only by the recipient. Even the service provider cannot read them. "
        "Like sending a letter in a lockbox that only the recipient has the key to."
    ),
}

GLOSSARY_JA = {
    "APIラッパー比率": (
        "外部サービス（OpenAI、AWS等）を呼び出すだけのコードの割合。"
        "たとえるなら「冷凍食品を温めて出すだけのレストラン」のようなもの。"
        "高いほど独自技術がなく、他社のサービスに完全に依存しています。"
    ),
    "CI/CD": (
        "継続的インテグレーション/継続的デリバリー。開発者がコードを変更するたびに"
        "自動でテスト・デプロイする仕組み。工場の品質検査ラインのようなもの。"
        "これがないと品質チェックが人手頼みで、不良品が出荷されるリスクがあります。"
    ),
    "ラッシュコミット": (
        "24時間以内に20件以上のコード変更が集中すること。"
        "手作業なら「締め切り前の徹夜」を疑いますが、AI開発ツール（Claude Code等）を"
        "使えばフードプロセッサーで調理するように高速開発は普通です。"
    ),
    "依存パッケージ数": (
        "プロジェクトが利用している外部ライブラリの数。料理のレシピの材料数のようなもの。"
        "多いほど機能は豊富ですが、どれか一つに問題が起きると全体に影響します。"
    ),
    "整合性スコア": (
        "ドキュメントの主張と実際のコードがどれだけ一致しているか（0〜100%）。"
        "レストランのメニュー写真と実際に出てくる料理がどれだけ一致するか、のようなもの。"
    ),
    "レッドフラグ": (
        "分析中に発見された警告サイン。保健所の検査レポートのようなもの。"
        "INFO（軽微な注意点）からCRITICAL（投資判断を左右する重大な問題）まで5段階。"
    ),
    "Gitフォレンジック": (
        "バージョン管理の履歴分析。建物の施工記録を確認するようなもの。"
        "丁寧に建てたのか、急いで建てたのかが分かります。"
    ),
    "テストカバレッジ": (
        "自動テストでカバーされているコードの割合。自動車メーカーの部品検査のようなもの。"
        "高いほど隠れた欠陥が少なく、信頼性が高いことを示します。"
    ),
    "モノレポ": (
        "フロントエンド＋バックエンド＋モバイルアプリ等を1つのリポジトリで管理する構成。"
        "百貨店（1棟に全テナント）と専門店（別々の建物）の違い。"
        "依存パッケージ数が多いのは構造上の特性です。"
    ),
    "技術的負債": (
        "開発を急ぐために取ったショートカットの蓄積。仮設材料で急いで建てた家のようなもの。"
        "今は動きますが、時間が経つほど修繕コストが膨らみます。"
    ),
    "E2EE": (
        "エンドツーエンド暗号化。送信者の端末で暗号化し、受信者だけが解読できる方式。"
        "受取人だけが鍵を持つ金庫で手紙を送るようなもの。"
        "サービス運営者でさえ中身を読めません。"
    ),
    "マッチ率": (
        "サービスサイトやドキュメントの主張が、実際のソースコードでどれだけ実現されているかの割合。"
        "100%なら「言っていることが全て実装されている」、0%なら「口だけで実態がない」ことを意味します。"
    ),
}


# ---------------------------------------------------------------------------
# 評価基準定義
# ---------------------------------------------------------------------------

# v0.3: 5-dimension scoring (Security Posture merged into Architecture Quality).
# Weights rebalanced to equal 20% each for a clean, interpretable distribution.
DIMENSIONS_EN = [
    {
        "name": "Technical Originality",
        "weight": "20%",
        "what": "How much of the code is genuinely original vs. calling external APIs",
        "levels": "Lv.1 (Copy) → Lv.5 (Extended) → Lv.10 (Frontier/paradigm-shifting)",
        "analogy": "A chef creating original recipes vs. reheating frozen meals",
    },
    {
        "name": "Technology Advancement",
        "weight": "20%",
        "what": "How modern and forward-looking the technology choices are",
        "levels": "Lv.1 (Legacy/10yr old) → Lv.5 (Current standard) → Lv.10 (5yr ahead)",
        "analogy": "Driving a classic car vs. industry standard vs. prototype electric vehicle",
    },
    {
        "name": "Implementation Depth",
        "weight": "20%",
        "what": "Is this a prototype or production-ready software?",
        "levels": "Lv.1 (UI mockup) → Lv.5 (Beta with tests) → Lv.10 (Mission-critical grade)",
        "analogy": "A concept car vs. a test model vs. an FDA-approved medical device",
    },
    {
        "name": "Architecture Quality (incl. Security Posture)",
        "weight": "20%",
        "what": "How well-organized and maintainable the codebase is, including security maturity "
                "(encryption, auth, vulnerability management)",
        "levels": "Lv.1 (Spaghetti + negligent security) → Lv.5 (Clean separation + industry-standard security) "
                  "→ Lv.10 (Distributed + military-grade security)",
        "analogy": "A cluttered unlocked shed vs. an organized office with keycards vs. a smart bank vault",
    },
    {
        "name": "Claim Consistency",
        "weight": "20%",
        "what": "Do the team's documentation claims match the actual code?",
        "levels": "Lv.1 (Fabricated claims) → Lv.5 (50% verifiable) → Lv.10 (Fully transparent)",
        "analogy": "A menu photo vs. the actual dish — how close is the match?",
    },
]

DIMENSIONS_JA = [
    {
        "name": "技術独自性 (Technical Originality)",
        "weight": "20%",
        "what": "コードがどの程度オリジナルか。外部APIを呼ぶだけか、独自ロジックがあるか",
        "levels": "Lv.1（コピー）→ Lv.5（拡張あり）→ Lv.10（パラダイム転換級）",
        "analogy": "冷凍食品を温めるだけの店 vs. オリジナルレシピの名店",
    },
    {
        "name": "技術先進性 (Technology Advancement)",
        "weight": "20%",
        "what": "技術選定がどの程度先進的か",
        "levels": "Lv.1（10年前の技術）→ Lv.5（業界標準）→ Lv.10（5年先を行く）",
        "analogy": "クラシックカー vs. 最新の量産車 vs. プロトタイプEV",
    },
    {
        "name": "実装深度 (Implementation Depth)",
        "weight": "20%",
        "what": "プロトタイプか、本番運用レベルか",
        "levels": "Lv.1（UIモックのみ）→ Lv.5（テスト付きベータ）→ Lv.10（ミッションクリティカル級）",
        "analogy": "コンセプトカー vs. テスト車両 vs. FDA認可の医療機器",
    },
    {
        "name": "アーキテクチャ品質（セキュリティ態勢を含む）(Architecture Quality incl. Security)",
        "weight": "20%",
        "what": "コードの整理度・保守性・拡張性に加え、セキュリティ成熟度（暗号化・認証・脆弱性管理）も統合評価",
        "levels": "Lv.1（スパゲッティ＋無防備）→ Lv.5（責務分離＋業界標準セキュリティ）→ Lv.10（分散＋軍事レベルセキュリティ）",
        "analogy": "鍵のない散らかった物置 vs. カードキー付き整理されたオフィス vs. スマート銀行金庫室",
    },
    {
        "name": "主張整合性 (Claim Consistency)",
        "weight": "20%",
        "what": "ドキュメントやWebサイトの主張が、実際のコードと一致しているか",
        "levels": "Lv.1（虚偽）→ Lv.5（50%検証可）→ Lv.10（完全透明）",
        "analogy": "メニュー写真と実際の料理 — どれだけ一致するか",
    },
]


# ---------------------------------------------------------------------------
# メイン生成関数
# ---------------------------------------------------------------------------

def generate_prompt(
    result: AnalysisResult,
    lang: str = "en",
    stage: str = "unknown",
) -> str:
    """IDE AI向けの構造化プロンプトを生成する。

    Args:
        result: DDE ヒューリスティック分析結果。
        lang: 出力言語 ("en" or "ja")。
        stage: スタートアップのステージ ("seed", "series_a", "series_b", "growth", "unknown")。

    Returns:
        IDE AI にそのまま渡せる構造化プロンプト文字列。
    """
    if lang == "ja":
        return _generate_ja(result, stage)
    return _generate_en(result, stage)


def _generate_en(result: AnalysisResult, stage: str) -> str:
    """English prompt generation."""
    sections: list[str] = []

    sections.append(_HEADER_EN)
    sections.append("## Glossary (for non-technical readers)\n")
    for term, definition in GLOSSARY_EN.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## Heuristic Analysis Results (automated, no AI used)\n")
    sections.append(_format_heuristic_en(result))

    sections.append("## Match Rate: Claims vs. Reality\n")
    sections.append(_format_match_rate_en(result))

    sections.append("## Red Flags Detected\n")
    sections.append(_format_red_flags_en(result))

    sections.append("## Scoring Framework (6 dimensions, 10-level scale)\n")
    sections.append(
        "Evaluate each dimension on a 1-10 scale, then convert to 0-100 points.\n"
        "Final score = weighted average of all dimensions.\n"
    )
    for dim in DIMENSIONS_EN:
        sections.append(
            f"### {dim['name']} (Weight: {dim['weight']})\n"
            f"**What to evaluate**: {dim['what']}\n"
            f"**Scale**: {dim['levels']}\n"
            f"**In plain terms**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_en(stage))
    sections.append(_EVAL_INSTRUCTIONS_EN)
    sections.append(_SITE_ANALYSIS_PROMPT_EN)
    sections.append(_QUESTION_INSTRUCTIONS_EN)

    return "\n".join(sections)


def _generate_ja(result: AnalysisResult, stage: str) -> str:
    """Japanese prompt generation."""
    sections: list[str] = []

    sections.append(_HEADER_JA)
    sections.append("## 用語集（IT業界外の方向け — ほんやくコンニャク）\n")
    for term, definition in GLOSSARY_JA.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## ヒューリスティック分析結果（自動分析・AI不使用）\n")
    sections.append(_format_heuristic_ja(result))

    sections.append("## マッチ率: 主張 vs 実態\n")
    sections.append(_format_match_rate_ja(result))

    sections.append("## 検出されたレッドフラグ（警告サイン）\n")
    sections.append(_format_red_flags_ja(result))

    sections.append("## スコアリング基準（6次元 × 10段階評価）\n")
    sections.append(
        "各次元を1〜10で評価し、100点満点に変換してください。\n"
        "最終スコア = 全次元の加重平均です。\n"
    )
    for dim in DIMENSIONS_JA:
        sections.append(
            f"### {dim['name']}（重み: {dim['weight']}）\n"
            f"**評価観点**: {dim['what']}\n"
            f"**尺度**: {dim['levels']}\n"
            f"**たとえるなら**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_ja(stage))
    sections.append(_EVAL_INSTRUCTIONS_JA)
    sections.append(_SITE_ANALYSIS_PROMPT_JA)
    sections.append(_QUESTION_INSTRUCTIONS_JA)

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Match Rate（主張 vs 実態の一致度）
# ---------------------------------------------------------------------------

def _format_match_rate_en(result: AnalysisResult) -> str:
    consistency = result.consistency
    total_claims = len(consistency.verified_claims) + len(consistency.unverified_claims)
    if total_claims == 0:
        return "No claims found in documentation to verify.\n"

    match_rate = len(consistency.verified_claims) / total_claims * 100
    bar = _make_bar(match_rate)

    lines = [
        f"**Overall Match Rate**: {match_rate:.0f}%",
        f"```",
        f"Claims vs Code: {bar} {match_rate:.0f}%",
        f"```",
        f"",
        f"| Category | Count | Meaning |",
        f"|----------|-------|---------|",
        f"| ✅ Verified | {len(consistency.verified_claims)} | Claims confirmed by actual code — \"they do what they say\" |",
        f"| ❓ Unverified | {len(consistency.unverified_claims)} | Claims not found in code — could be future plans, or overstatement |",
        f"| ❌ Contradictions | {len(consistency.contradictions)} | Claims that directly conflict with code — potential deception |",
        f"",
        f"**What this means**: A match rate above 70% suggests the team is honest about their capabilities. "
        f"Below 50% is a warning sign — the team may be overpromising. "
        f"Contradictions are the most serious: they suggest the team knows the truth but says otherwise.",
        f"",
    ]
    return "\n".join(lines)


def _format_match_rate_ja(result: AnalysisResult) -> str:
    consistency = result.consistency
    total_claims = len(consistency.verified_claims) + len(consistency.unverified_claims)
    if total_claims == 0:
        return "ドキュメントに検証可能な主張が見つかりませんでした。\n"

    match_rate = len(consistency.verified_claims) / total_claims * 100
    bar = _make_bar(match_rate)

    lines = [
        f"**全体マッチ率**: {match_rate:.0f}%",
        f"```",
        f"主張 vs コード: {bar} {match_rate:.0f}%",
        f"```",
        f"",
        f"| 区分 | 件数 | 意味 |",
        f"|------|------|------|",
        f"| ✅ 検証済み | {len(consistency.verified_claims)} | 実際のコードで確認できた主張 — 「言った通りのことを実装している」 |",
        f"| ❓ 未検証 | {len(consistency.unverified_claims)} | コード内に証拠が見つからない — 将来の計画か、過大な主張の可能性 |",
        f"| ❌ 矛盾 | {len(consistency.contradictions)} | コードと矛盾する主張 — 事実と異なることを述べている可能性 |",
        f"",
        f"**見方**: マッチ率70%以上ならチームは技術力について誠実と判断できます。",
        f"50%未満は要注意 — 実力以上のことを主張している可能性があります。",
        f"矛盾が最も深刻で、「事実を知っていながら異なる説明をしている」ことを示唆します。",
        f"",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Heuristic formatting
# ---------------------------------------------------------------------------

def _format_heuristic_en(result: AnalysisResult) -> str:
    code = result.code_analysis
    git = result.git_forensics
    consistency = result.consistency
    doc = result.doc_analysis

    lines = [
        "### Code Analysis\n",
        f"| Metric | Value | What this means |",
        f"|--------|-------|-----------------|",
        f"| Total files | {code.total_files:,} | Number of source code files in the project |",
        f"| Total lines | {code.total_lines:,} | Lines of code (larger = more substantial product) |",
        f"| Languages | {_format_langs(code.languages)} | Programming languages used |",
        f"| API wrapper ratio | {code.api_wrapper_ratio:.1%} | % of code that just calls external services (lower = more original) |",
        f"| Has tests | {'Yes ✓' if code.has_tests else 'No ✗'} | Whether automated quality checks exist |",
        f"| Has CI/CD | {'Yes ✓' if code.has_ci_cd else 'No ✗'} | Whether automated build/deploy pipeline exists |",
        f"| Has documentation | {'Yes ✓' if code.has_documentation else 'No ✗'} | Whether technical docs exist |",
        f"| Dependency count | {code.dependency_count} | Number of external libraries used |",
        "",
        "### Git History Analysis (reading the development story)\n",
        f"| Metric | Value | What this means |",
        f"|--------|-------|-----------------|",
        f"| Total commits | {git.total_commits:,} | Number of code changes recorded (the project's diary) |",
        f"| Unique authors | {git.unique_authors} | Number of developers who contributed |",
        f"| First commit | {git.first_commit_date or 'N/A'} | When development started |",
        f"| Last commit | {git.last_commit_date or 'N/A'} | Most recent activity |",
        f"| High-velocity window ratio | {git.rush_commit_ratio:.1%} | % of time windows with dense commits (INFORMATIONAL ONLY — do NOT score) |",
        "",
        "### Document & Claim Analysis\n",
        f"| Metric | Value | What this means |",
        f"|--------|-------|-----------------|",
        f"| Total claims found | {len(doc.claims)} | Statements about technology/performance in docs |",
        f"| Performance claims | {len(doc.performance_claims)} | Claims about speed, scale, uptime |",
        f"| Architecture claims | {len(doc.architecture_claims)} | Claims about system design, patents |",
        f"| Verified claims | {len(consistency.verified_claims)} | Claims confirmed by actual code |",
        f"| Unverified claims | {len(consistency.unverified_claims)} | Claims not found in code |",
        f"| Contradictions | {len(consistency.contradictions)} | Claims that conflict with code |",
        f"| Consistency score | {consistency.consistency_score:.1f}% | Overall match between claims and code |",
        "",
    ]
    return "\n".join(lines)


def _format_heuristic_ja(result: AnalysisResult) -> str:
    code = result.code_analysis
    git = result.git_forensics
    consistency = result.consistency
    doc = result.doc_analysis

    lines = [
        "### コード分析\n",
        f"| 指標 | 値 | 意味 |",
        f"|------|-----|------|",
        f"| 総ファイル数 | {code.total_files:,} | プロジェクト内のソースコードファイル数 |",
        f"| 総行数 | {code.total_lines:,} | 書かれたコードの行数（多いほど実質的な製品） |",
        f"| 使用言語 | {_format_langs(code.languages)} | 使用されているプログラミング言語 |",
        f"| APIラッパー比率 | {code.api_wrapper_ratio:.1%} | 外部サービスを呼ぶだけのコードの割合（低いほど独自性が高い） |",
        f"| テスト有無 | {'あり ✓' if code.has_tests else 'なし ✗'} | 自動品質チェックが存在するか |",
        f"| CI/CD有無 | {'あり ✓' if code.has_ci_cd else 'なし ✗'} | 自動ビルド・デプロイの仕組みがあるか |",
        f"| ドキュメント有無 | {'あり ✓' if code.has_documentation else 'なし ✗'} | 技術文書が存在するか |",
        f"| 依存パッケージ数 | {code.dependency_count} | 外部ライブラリの数 |",
        "",
        "### Git履歴分析（開発の歩みを読み解く）\n",
        f"| 指標 | 値 | 意味 |",
        f"|------|-----|------|",
        f"| 総コミット数 | {git.total_commits:,} | 記録されたコード変更の回数（プロジェクトの日記帳） |",
        f"| 開発者数 | {git.unique_authors} | コードに貢献した人数 |",
        f"| 開発開始日 | {git.first_commit_date or 'N/A'} | 最初のコード変更日 |",
        f"| 最終更新日 | {git.last_commit_date or 'N/A'} | 最新の活動日 |",
        f"| 高速コミット窓率 | {git.rush_commit_ratio:.1%} | 短時間に集中したコミット窓の割合（参考値のみ — スコアリングには反映しないこと） |",
        "",
        "### ドキュメント・主張分析\n",
        f"| 指標 | 値 | 意味 |",
        f"|------|-----|------|",
        f"| 検出された主張数 | {len(doc.claims)} | 技術力やパフォーマンスに関する記述の数 |",
        f"| 性能に関する主張 | {len(doc.performance_claims)} | 速度・規模・稼働率に関する主張 |",
        f"| 設計に関する主張 | {len(doc.architecture_claims)} | システム設計・特許に関する主張 |",
        f"| 検証済み主張 | {len(consistency.verified_claims)} | 実際のコードで確認できた主張 |",
        f"| 未検証主張 | {len(consistency.unverified_claims)} | コード内に証拠が見つからない主張 |",
        f"| 矛盾 | {len(consistency.contradictions)} | コードと矛盾する主張 |",
        f"| 整合性スコア | {consistency.consistency_score:.1f}% | 主張とコードの全体的な一致度 |",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Red flag formatting
# ---------------------------------------------------------------------------

def _format_red_flags_en(result: AnalysisResult) -> str:
    all_flags = _collect_flags(result)
    if not all_flags:
        return "No red flags detected.\n"

    lines: list[str] = []
    severity_labels = {
        "critical": "🔴 CRITICAL (potential deal-breaker — like finding structural damage in a building)",
        "high": "🟠 HIGH (significant concern — like a restaurant failing a hygiene inspection)",
        "medium": "🟡 MEDIUM (worth investigating — like an unusual item on a financial statement)",
        "low": "🔵 LOW (minor note — like a cosmetic scratch on a car)",
        "info": "ℹ️  INFO (for reference only)",
    }

    for severity in ["critical", "high", "medium", "low", "info"]:
        flags = [f for f in all_flags if f.severity.value == severity]
        if flags:
            lines.append(f"### {severity_labels[severity]}\n")
            for flag in flags:
                lines.append(f"- **{flag.title}**: {flag.description}")
            lines.append("")

    return "\n".join(lines)


def _format_red_flags_ja(result: AnalysisResult) -> str:
    all_flags = _collect_flags(result)
    if not all_flags:
        return "レッドフラグは検出されませんでした。\n"

    lines: list[str] = []
    severity_labels = {
        "critical": "🔴 CRITICAL — 投資判断を左右する重大な問題（建物の構造欠陥のようなもの）",
        "high": "🟠 HIGH — 要注意（衛生検査に不合格のレストランのようなもの）",
        "medium": "🟡 MEDIUM — 追加調査推奨（決算書の不自然な項目のようなもの）",
        "low": "🔵 LOW — 軽微な注意点（車の小さな傷のようなもの）",
        "info": "ℹ️  INFO — 参考情報",
    }

    for severity in ["critical", "high", "medium", "low", "info"]:
        flags = [f for f in all_flags if f.severity.value == severity]
        if flags:
            lines.append(f"### {severity_labels[severity]}\n")
            for flag in flags:
                lines.append(f"- **{flag.title}**: {flag.description}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage context
# ---------------------------------------------------------------------------

def _get_stage_context_en(stage: str) -> str:
    contexts = {
        "seed": (
            "## Stage Context: Seed\n\n"
            "At the seed stage, expect:\n"
            "- Smaller codebases (1K-10K lines is normal)\n"
            "- 1-3 developers\n"
            "- Limited or no CI/CD (acceptable at this stage)\n"
            "- Focus on: Does the core idea work? Is there genuine technical capability?\n"
            "- Red flags: API-only wrappers, no original code, fabricated claims\n"
        ),
        "series_a": (
            "## Stage Context: Series A\n\n"
            "At Series A, expect:\n"
            "- Medium codebases (10K-100K lines)\n"
            "- 3-10 developers\n"
            "- Basic CI/CD and tests should exist\n"
            "- Focus on: Is the architecture scalable? Is the team growing effectively?\n"
            "- Red flags: No tests, no CI/CD, single-developer dependency\n"
        ),
        "series_b": (
            "## Stage Context: Series B\n\n"
            "At Series B, expect:\n"
            "- Large codebases (100K+ lines)\n"
            "- 10+ developers with comprehensive CI/CD and testing\n"
            "- Focus on: Scalability, security, technical debt management\n"
            "- Red flags: Poor security, no monitoring, high tech debt\n"
        ),
        "growth": (
            "## Stage Context: Growth/Late Stage\n\n"
            "At growth stage, expect:\n"
            "- Very large codebases (500K+ lines) with 30+ developers\n"
            "- Enterprise-grade CI/CD, security, and compliance\n"
            "- Focus on: Operational excellence, compliance, disaster recovery\n"
            "- Red flags: Compliance gaps, scalability bottlenecks\n"
        ),
    }
    return contexts.get(stage, (
        "## Stage Context\n\n"
        "The startup's development stage was not specified. "
        "When evaluating, consider whether the findings are appropriate "
        "for the company's current phase (seed → Series A → Series B → growth).\n"
    ))


def _get_stage_context_ja(stage: str) -> str:
    contexts = {
        "seed": (
            "## ステージ別の判断基準: シード期\n\n"
            "シード期では以下が一般的です:\n"
            "- コード規模: 1,000〜10,000行程度\n"
            "- 開発者: 1〜3名\n"
            "- CI/CDやテストは未整備でも許容範囲\n"
            "- 重要な評価ポイント: コアのアイデアは動くか？ 本物の技術力があるか？\n"
            "- この段階でのレッドフラグ: API呼び出しだけ、独自コードなし、虚偽の主張\n"
        ),
        "series_a": (
            "## ステージ別の判断基準: シリーズA\n\n"
            "シリーズAでは以下が期待されます:\n"
            "- コード規模: 10,000〜100,000行\n"
            "- 開発者: 3〜10名\n"
            "- 基本的なCI/CDとテストが存在すべき\n"
            "- 重要な評価ポイント: 設計は拡張可能か？ チームは成長しているか？\n"
            "- この段階でのレッドフラグ: テストなし、CI/CDなし、一人依存\n"
        ),
        "series_b": (
            "## ステージ別の判断基準: シリーズB\n\n"
            "シリーズBでは以下が期待されます:\n"
            "- コード規模: 100,000行以上\n"
            "- 開発者: 10名以上。包括的なCI/CD・テストが必須\n"
            "- 重要な評価ポイント: スケーラビリティ、セキュリティ、技術的負債の管理\n"
            "- この段階でのレッドフラグ: セキュリティ不備、監視なし、技術的負債過大\n"
        ),
        "growth": (
            "## ステージ別の判断基準: グロース/レイト\n\n"
            "グロース段階では以下が期待されます:\n"
            "- コード規模: 500,000行以上、開発者30名以上\n"
            "- エンタープライズ級のCI/CD、セキュリティ、コンプライアンス\n"
            "- 重要な評価ポイント: 運用の卓越性、コンプライアンス、災害復旧\n"
            "- この段階でのレッドフラグ: コンプライアンス不備、スケーラビリティの壁\n"
        ),
    }
    return contexts.get(stage, (
        "## ステージ別の判断基準\n\n"
        "スタートアップの開発ステージが指定されていません。\n"
        "評価時は、発見事項がそのステージ（シード → シリーズA → シリーズB → グロース）\n"
        "に対して適切かどうかを考慮してください。\n"
    ))


# ---------------------------------------------------------------------------
# Header / Instructions templates
# ---------------------------------------------------------------------------

_HEADER_EN = """# DDE Technical Due Diligence — AI Evaluation Prompt

> **How to use**: This prompt was generated by [DDE (Due Diligence Engine)](https://github.com/taka-avantgarde/Due-diligence-engine).
> Paste this entire output into your AI terminal (Claude Code, Cursor, GitHub Copilot, etc.)
> and the AI will evaluate the project using the data below.
>
> **No API keys required** — your IDE's AI subscription handles the analysis cost.
>
> **For non-technical readers**: A glossary of technical terms is included below.
> All metrics include plain-language explanations. Think of this as a "translation device"
> that converts engineering jargon into business language.
"""

_HEADER_JA = """# DDE テクニカルデューデリジェンス — AI評価プロンプト

> **使い方**: このプロンプトは [DDE (Due Diligence Engine)](https://github.com/taka-avantgarde/Due-diligence-engine) が自動生成しました。
> この出力全体を AI ターミナル（Claude Code, Cursor, GitHub Copilot 等）に貼り付けると、
> AI がデータを読み取って評価レポートを作成します。
>
> **APIキー不要** — お使いのIDEのAIサブスクリプションで分析できます。
>
> **IT業界以外の方へ**: 下記に「ほんやくコンニャク」（用語集）を掲載しています。
> エンジニア用語をビジネス言語に翻訳し、各指標の「意味」列で平易に説明しています。
"""

_EVAL_INSTRUCTIONS_EN = """## Your Evaluation Task

Based on the heuristic data above, perform the following:

1. **Read all code in the repository** to verify and supplement the heuristic findings
2. **Score each of the 6 dimensions** on a 1-10 scale with evidence and plain-language explanation
3. **Calculate the final score**: Each level × 10 = points (0-100), then weighted average
4. **Assign a grade**: A (90+), B (75+), C (60+), D (40+), F (<40)
5. **Re-evaluate red flags**: The heuristic analysis may have false positives
   - Rush commits from AI-assisted development are normal, not suspicious
   - Technical terms (E2EE, Signal Protocol) are not "buzzwords" if actually implemented
   - High dependency counts in monorepos are structural, not a risk
6. **Identify strengths**: What this technology enables — give concrete examples
   - "Because this feature exists, users can do X"
   - "This architecture allows the system to handle Y"
7. **Identify weaknesses**: What could go wrong and why it matters
8. **Recommend improvements**: "If you do X, you could also achieve Y"
9. **Generate investor questions**: Plain language questions for non-technical investors

### Output Format

Use status bars for visual scoring (copy this format exactly):

```
## DDE AI Evaluation Report: {Project Name}

### Overall Score
██████████████████░░░░░░░░░░░░░░ 87/100 (Grade: B)

### Dimension Scores (status bar + plain language)

Technical Originality (25%)
████████████████████████████░░░░ 92/100 — Lv.9 Original
→ In plain terms: [explanation of what this means for a non-engineer]
→ This enables: [what the user/business can do because of this]

Technology Advancement (20%)
██████████████████████████░░░░░░ 88/100 — Lv.9 Leading-Edge
→ In plain terms: [explanation]
→ This enables: [capability]

[...repeat for all 6 dimensions...]

### Strengths — What This Technology Makes Possible
1. [Strength] → "Because of this, [concrete capability/benefit]"
2. ...

### Weaknesses — What Could Go Wrong
1. [Weakness] → "This matters because [real-world impact]"
2. ...

### Red Flag Re-evaluation
| Heuristic Flag | AI Assessment | Verdict |
|----------------|---------------|---------|

### Match Rate: Claims vs Reality
Claims Match: ██████████████████████░░░░░░░░░░ 72%
→ [plain language explanation]

### How to Improve — "If you do X, Y becomes possible"
1. [Improvement] → "This would enable [new capability]"
2. ...

### Questions for the Startup Team
1. ...
```
"""

_EVAL_INSTRUCTIONS_JA = """## あなたへの評価タスク

上記のヒューリスティックデータに基づいて、以下を実行してください:

1. **リポジトリ内の全コードを読み**、ヒューリスティック結果を検証・補足
2. **6次元それぞれを1〜10で評価**（根拠＋平易な日本語での説明を添えて）
3. **最終スコアを計算**: 各レベル × 10 = ポイント（0〜100）→ 加重平均
4. **グレードを付与**: A（90以上）、B（75以上）、C（60以上）、D（40以上）、F（40未満）
5. **レッドフラグの再評価**: ヒューリスティック分析には誤検知がありえます
   - AI駆動開発によるラッシュコミットは正常（不審ではない）
   - E2EEやSignal Protocol等は実装済みなら「バズワード」ではない
   - モノレポの依存数が多いのは構造的特性（リスクではない）
6. **強みの分析**: この技術で何が可能になるか — 具体例を挙げて
   - 「この機能があるおかげで、ユーザーは○○ができます」
   - 「このアーキテクチャにより、△△が可能になっています」
7. **弱みの分析**: 何が起こりうるか、なぜ問題か
8. **改善提案**: 「○○すれば、さらに△△もできるようになるかもしれません」
9. **投資家向け質問**: 非技術者でも聞ける平易な表現で

### 出力フォーマット

ステータスバーでスコアを視覚的に表示してください:

```
## DDE AI評価レポート: {プロジェクト名}

### 総合スコア
██████████████████░░░░░░░░░░░░░░ 87/100（グレード: B）

### 次元別スコア（ステータスバー＋平易な解説）

技術独自性（25%）
████████████████████████████░░░░ 92/100 — Lv.9 オリジナル
→ わかりやすく言うと: [エンジニア以外にもわかる説明]
→ この技術のおかげで: [何ができるようになっているか]

技術先進性（20%）
██████████████████████████░░░░░░ 88/100 — Lv.9 先端的
→ わかりやすく言うと: [説明]
→ この技術のおかげで: [できること]

[...6次元すべて繰り返し...]

### 強み — この技術で何ができるようになっているか
1. [強み] → 「これがあるおかげで、[具体的にできること・事例]」
2. ...

### 弱み — 何が起こりうるか
1. [弱み] → 「なぜ問題かというと、[実際の影響]」
2. ...

### レッドフラグ再評価
| ヒューリスティックの指摘 | AI評価 | 判定 |
|--------------------------|--------|------|

### マッチ率: 主張 vs 実態
主張の一致度: ██████████████████████░░░░░░░░░░ 72%
→ [平易な解説]

### こうすればもっと良くなる — 「○○すれば△△も可能に」
1. [改善策] → 「これにより、[新たに可能になること]」
2. ...

### スタートアップチームへの質問
1. ...
```
"""

_SITE_ANALYSIS_PROMPT_EN = """## Optional: Service Site Cross-Validation

**Want to check if the company's website claims match their actual code?**

If you have access to the company's service website or product page, paste the URL below
and the AI will:
1. Read the website content
2. Compare claims against the code analysis above
3. Calculate a **Website Claim Match Rate** — how much of what they say is actually implemented
4. Flag any exaggerations or outright fabrications

This is like comparing a restaurant's menu photos with the actual dishes served.

```
Service site URL: [paste URL here if available]
```

If a URL is provided above, add this section to your report:

```
### Website vs Code — Claim Verification
Website Match Rate: ██████████████████░░░░░░░░░░░░░░ 65%

| Website Claim | Code Evidence | Match? |
|---------------|---------------|--------|
| "AI-powered analysis" | Found: OpenAI API calls only | ❌ Overstated |
| "End-to-end encryption" | Found: libsignal implementation | ✅ Verified |
| ... | ... | ... |

→ [Plain language summary of findings]
```
"""

_SITE_ANALYSIS_PROMPT_JA = """## オプション: サービスサイトとのクロス検証

**企業のWebサイトの主張が、実際のコードと一致しているか確認したいですか？**

サービスサイトやプロダクトページのURLがあれば、以下に貼り付けてください。
AIが以下を実行します:
1. Webサイトの内容を読み取り
2. 上記のコード分析結果と主張を照合
3. **Webサイト主張マッチ率**を算出 — 言っていることがどれだけ実装されているか
4. 誇張や虚偽の主張をフラグ付け

メニューの写真と実際に出てくる料理を比較するようなものです。

```
サービスサイトURL: [ここにURLを貼り付け]
```

URLが提供された場合は、レポートに以下のセクションを追加してください:

```
### Webサイト vs コード — 主張の検証
Webサイトマッチ率: ██████████████████░░░░░░░░░░░░░░ 65%

| Webサイトの主張 | コード上の証拠 | 一致? |
|-----------------|----------------|-------|
| 「AI分析搭載」 | 見つかった: OpenAI API呼び出しのみ | ❌ 過大表現 |
| 「エンドツーエンド暗号化」 | 見つかった: libsignal実装 | ✅ 検証済み |
| ... | ... | ... |

→ [平易な言葉での発見事項のまとめ]
```
"""

_QUESTION_INSTRUCTIONS_EN = """## Auto-Generate Questions for the Startup

Based on your analysis, generate 5-10 questions that an investor should ask the startup team.
**Use plain language that a non-technical investor can ask confidently.**

Focus on:
- Areas where claims could not be verified — "Your website says X, but we couldn't find evidence of X in the code. Can you explain?"
- Missing safeguards — "What happens if your main server goes down? Is there a backup plan?"
- Growth readiness — "If your users grow 10x, what needs to change in your technology?"
- Team risk — "How many people can maintain this system? What happens if the lead developer leaves?"
- Improvement plans — "What are your top 3 technical priorities for the next 6 months?"
- Data protection — "How do you protect user data? Have you had a security audit?"
"""

_QUESTION_INSTRUCTIONS_JA = """## スタートアップへの質問を自動生成

分析結果に基づき、投資家がスタートアップに聞くべき質問を5〜10個生成してください。
**IT用語を避け、非技術系の投資家が自信を持って聞ける表現にしてください。**

以下に焦点を当ててください:
- コードで検証できなかった主張 — 「御社のサイトには○○と書かれていますが、コード上では確認できませんでした。詳しく教えていただけますか？」
- 安全装置の不足 — 「メインサーバーが止まった場合、バックアップ体制はどうなっていますか？」
- 成長への備え — 「ユーザーが10倍に増えた場合、技術面で何を変える必要がありますか？」
- チームリスク — 「このシステムを維持できる人は何人いますか？ 主要開発者が抜けた場合は？」
- 改善計画 — 「今後6ヶ月の技術面での最優先課題は何ですか？」
- データ保護 — 「ユーザーデータの保護はどのように行っていますか？ セキュリティ監査を受けたことは？」
"""


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _make_bar(value: float, width: int = 30) -> str:
    """Generate a status bar: ██████████░░░░░░░░░░"""
    filled = int(value / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def _format_langs(languages: dict[str, int]) -> str:
    if not languages:
        return "N/A"
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    top = sorted_langs[:5]
    parts = [f"{lang} ({count:,})" for lang, count in top]
    if len(sorted_langs) > 5:
        parts.append(f"+{len(sorted_langs) - 5} more")
    return ", ".join(parts)


def _collect_flags(result: AnalysisResult) -> list[RedFlag]:
    flags: list[RedFlag] = []
    flags.extend(result.code_analysis.red_flags)
    flags.extend(result.doc_analysis.red_flags)
    flags.extend(result.git_forensics.red_flags)
    flags.extend(result.consistency.red_flags)
    return flags


# ===========================================================================
# Consulting Prompt (--pdf mode)
# ===========================================================================


def generate_consulting_prompt(
    result: AnalysisResult,
    lang: str = "en",
    stage: str = "unknown",
    urls: list[str] | None = None,
) -> str:
    """Generate an enhanced prompt that instructs IDE AI to produce JSON + PDF.

    When ``dde prompt --pdf`` is used, this prompt replaces the standard one.
    It includes:
      - All heuristic data (same as normal prompt)
      - Role assignment (world-class consultant)
      - SWOT / future outlook / strategic advice / investment thesis instructions
      - Site verification instructions (when URLs are provided)
      - Competitive analysis instructions (always)
      - Strict JSON output schema
      - ``dde report --consulting`` command to generate PDF
    """
    if lang == "ja":
        return _generate_consulting_ja(result, stage, urls=urls)
    return _generate_consulting_en(result, stage, urls=urls)


def _generate_consulting_en(result: AnalysisResult, stage: str, *, urls: list[str] | None = None) -> str:
    sections: list[str] = []

    sections.append(_CONSULTING_HEADER_EN)
    sections.append("## Glossary\n")
    for term, definition in GLOSSARY_EN.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## Heuristic Analysis Results\n")
    sections.append(_format_heuristic_en(result))

    sections.append("## Match Rate: Claims vs. Reality\n")
    sections.append(_format_match_rate_en(result))

    sections.append("## Red Flags Detected\n")
    sections.append(_format_red_flags_en(result))

    sections.append("## Scoring Framework (6 dimensions, 10-level scale)\n")
    for dim in DIMENSIONS_EN:
        sections.append(
            f"### {dim['name']} (Weight: {dim['weight']})\n"
            f"**Evaluate**: {dim['what']}\n"
            f"**Scale**: {dim['levels']}\n"
            f"**Analogy**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_en(stage))

    # Site verification (only when URLs are provided)
    if urls:
        url_list = "\n".join(f"  - {u}" for u in urls)
        sections.append(_SITE_VERIFICATION_INSTRUCTIONS_EN.format(url_list=url_list))

    # Competitive analysis (always included)
    sections.append(_COMPETITIVE_ANALYSIS_INSTRUCTIONS_EN)

    # Atlas 4-axis optimization evaluation (v2.0, always included)
    sections.append(_ATLAS_FOUR_AXIS_INSTRUCTIONS_EN)

    # Implementation Capability Matrix (v2.0, always included)
    sections.append(_IMPLEMENTATION_MATRIX_INSTRUCTIONS_EN)

    # Competitor Selection Rationales (v0.3.1, always included)
    sections.append(_COMPETITOR_RATIONALES_INSTRUCTIONS_EN)

    sections.append(_CONSULTING_EVAL_EN)
    sections.append(_CONSULTING_JSON_SCHEMA)
    sections.append(_consulting_pdf_command(result, "en"))

    return "\n".join(sections)


def _generate_consulting_ja(result: AnalysisResult, stage: str, *, urls: list[str] | None = None) -> str:
    sections: list[str] = []

    sections.append(_CONSULTING_HEADER_JA)
    sections.append("## 用語集\n")
    for term, definition in GLOSSARY_JA.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## ヒューリスティック分析結果\n")
    sections.append(_format_heuristic_ja(result))

    sections.append("## マッチ率: 主張 vs 実態\n")
    sections.append(_format_match_rate_ja(result))

    sections.append("## 検出されたレッドフラグ\n")
    sections.append(_format_red_flags_ja(result))

    sections.append("## スコアリング基準（6次元 × 10段階評価）\n")
    for dim in DIMENSIONS_JA:
        sections.append(
            f"### {dim['name']}（重み: {dim['weight']}）\n"
            f"**評価観点**: {dim['what']}\n"
            f"**尺度**: {dim['levels']}\n"
            f"**たとえ**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_ja(stage))

    # サイト検証（URLが提供された場合のみ）
    if urls:
        url_list = "\n".join(f"  - {u}" for u in urls)
        sections.append(_SITE_VERIFICATION_INSTRUCTIONS_JA.format(url_list=url_list))

    # 競合分析（常に含める）
    sections.append(_COMPETITIVE_ANALYSIS_INSTRUCTIONS_JA)

    # Atlas 4軸最適化評価（v2.0、常に含める）
    sections.append(_ATLAS_FOUR_AXIS_INSTRUCTIONS_JA)

    # 実装能力マトリックス（v2.0、常に含める）
    sections.append(_IMPLEMENTATION_MATRIX_INSTRUCTIONS_JA)

    # 競合選定理由（v0.3.1、常に含める）
    sections.append(_COMPETITOR_RATIONALES_INSTRUCTIONS_JA)

    sections.append(_CONSULTING_EVAL_JA)
    sections.append(_CONSULTING_JSON_SCHEMA)
    sections.append(_consulting_pdf_command(result, "ja"))

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Consulting-mode templates
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Site Verification & Competitive Analysis instruction templates
# ---------------------------------------------------------------------------

_SITE_VERIFICATION_INSTRUCTIONS_EN = """## Site Verification Task

The user provided the following product/service URLs for cross-validation:
{url_list}

**Visit each URL** (using WebFetch or browser tool), read the content, and evaluate the following 9 credibility items by comparing site claims against the codebase:

| # | Key | Item Name | What to Check |
|---|-----|-----------|---------------|
| 1 | feature_claim_match | Feature Claim Match | Do features listed on the site exist in the code? |
| 2 | tech_stack_consistency | Tech Stack Consistency | Does the tech stack described match actual dependencies? |
| 3 | security_claim_verification | Security Claim Verification | Are security claims (E2EE, encryption, etc.) implemented? |
| 4 | performance_claim_plausibility | Performance Claim Plausibility | Are performance numbers (speed, uptime) plausible from the code? |
| 5 | scale_claim_consistency | Scale Claim Consistency | Do scale claims (users, data volume) match infrastructure? |
| 6 | launch_date_verification | Launch Date Verification | Does the claimed launch timeline match git history? |
| 7 | pricing_feasibility | Pricing Model Feasibility | Is the pricing model sustainable given the tech stack costs? |
| 8 | compliance_display | Compliance Display Audit | Are required legal/compliance notices properly displayed? |
| 9 | ai_washing_index | AI-Washing Index | Are AI claims genuine or just buzzword decoration? |

**NOTE**: Team size / headcount evaluation is intentionally excluded. In the AI era,
lean teams + AI leverage is the winning pattern — headcount is not a quality signal.

For each item, assign:
- **score**: 0-100 (100 = perfectly consistent, 0 = completely fabricated)
- **confidence**: "high" | "medium" | "low"
- **rationale**: Evidence-based explanation
- **evidence**: List of specific URLs, file paths, or code snippets

Calculate **overall_credibility** as the weighted average of all 9 scores.
Provide a **summary** paragraph explaining the overall site credibility.

Include the results in the `site_verification` section of the JSON output.
"""

_SITE_VERIFICATION_INSTRUCTIONS_JA = """## サイト検証タスク

以下のプロダクト/サービスURLが検証用に提供されました:
{url_list}

**各URLにアクセス**（WebFetchまたはブラウザツール使用）し、サイトの内容を読み取り、コードベースと照合して以下の9項目の信頼性を評価してください:

| # | キー | 項目名 | チェック内容 |
|---|------|--------|-------------|
| 1 | feature_claim_match | 機能主張一致度 | サイトに記載された機能がコードに存在するか |
| 2 | tech_stack_consistency | 技術スタック整合性 | 記載された技術スタックが実際の依存関係と一致するか |
| 3 | security_claim_verification | セキュリティ主張検証 | セキュリティに関する主張（E2EE、暗号化等）が実装されているか |
| 4 | performance_claim_plausibility | パフォーマンス主張妥当性 | パフォーマンス数値（速度、稼働率）がコードから見て妥当か |
| 5 | scale_claim_consistency | 規模主張一貫性 | 規模に関する主張（ユーザー数、データ量）がインフラと整合するか |
| 6 | launch_date_verification | ローンチ日検証 | 主張するローンチ日がgit履歴と一致するか |
| 7 | pricing_feasibility | 料金モデル実現性 | 料金モデルが技術スタックのコストに対して持続可能か |
| 8 | compliance_display | コンプライアンス表示監査 | 法的・コンプライアンス表示が適切に行われているか |
| 9 | ai_washing_index | AIウォッシュ指数 | AI関連の主張が本物か、バズワード装飾に過ぎないか |

**注**: チーム規模・人数評価は意図的に除外。AI 時代は「少数精鋭 + AI レバレッジ」が勝ちパターンであり、
人数は品質シグナルにならない。

各項目について以下を付与:
- **score**: 0-100（100 = 完全に整合、0 = 完全に虚偽）
- **confidence**: "high" | "medium" | "low"
- **rationale**: エビデンスに基づく説明
- **evidence**: 具体的なURL、ファイルパス、コード断片のリスト

**overall_credibility** を全10項目のスコアの加重平均として算出。
**summary** で全体的なサイト信頼性を説明する段落を記述。

結果はJSON出力の `site_verification` セクションに含めてください。
"""

_COMPETITIVE_ANALYSIS_INSTRUCTIONS_EN = """## Competitive Analysis Task

Produce a comprehensive competitive analysis for the target company across **6 fixed markets**.
For each of the **7 chart types**, generate data for ALL 6 markets (one mini-chart per market).
Each chart page renders a 2×3 grid: [Global | US] [EMEA | LATAM] [Japan | SEA].

### Fixed 6 Markets (always these, in this order)
1. Global
2. US
3. EMEA
4. Japan
5. SEA
6. LATAM

### 7 Chart Types (each rendered as a 2×3 grid page)

1. **magic_quadrant** — Forrester Wave / Gartner Magic Quadrant
   - X: "Current Offering" — Feature breadth × API coverage × Documentation quality × Enterprise readiness (0-100)
   - Y: "Strategy" — Vision clarity × Roadmap ambition × Ecosystem play × Funding runway (0-100)
   - Quadrants: Leaders (high X, high Y) / Strong Performers (high X, low Y) / Contenders (low X, high Y) / Challengers (low X, low Y)

2. **bcg_matrix** — BCG Growth-Share Matrix
   - X: "Relative Market Share (log scale)" — Revenue vs #1 player × Install base × Developer mindshare (0-100, right = dominant)
   - Y: "Market Growth Rate" — TAM CAGR × New-segment creation × Geographic expansion velocity (0-100)
   - Quadrants: Stars (high-high) / Question Marks (low X, high Y) / Cash Cows (high X, low Y) / Dogs (low-low)

3. **mckinsey_moat** — McKinsey 9-Box / Tech Moat Matrix
   - X: "Competitive Position" — Switching cost × Data network effects × Integration lock-in × Brand premium (0-100)
   - Y: "Technical Moat Depth" — Algorithm uniqueness × Proprietary data × Latency edge × Model architecture originality (0-100)
   - Quadrants: Fortress (high-high) / Innovator (low X, high Y) / Entrenched (high X, low Y) / Commodity (low-low)

4. **security_posture** — Security & Privacy Maturity Matrix
   - X: "Security Implementation Depth" — Encryption at-rest & in-transit strength × Zero-trust architecture adoption × Penetration test cadence × Incident response maturity (0-100)
   - Y: "Privacy & Compliance Readiness" — GDPR/CCPA/HIPAA compliance level × Data minimization practice × Consent management sophistication × Privacy-by-design adoption (0-100)
   - Quadrants: Privacy Leader (high-high) / Security Fortress (high X, low Y) / Compliance Risk (low X, high Y) / Exposed (low-low)

5. **data_governance** — Data Governance & Transparency Matrix
   - X: "Data Protection Capability" — E2E encryption strength × Key management maturity × Data leak prevention (DLP) × Access control granularity × Secure deletion capability (0-100)
   - Y: "Transparency & Accountability" — Audit trail completeness × Data processing disclosure × Third-party audit frequency × Breach notification speed × Open-source security code ratio (0-100)
   - Quadrants: Trust Leader (high-high) / Opaque Fortress (high X, low Y) / Transparent but Vulnerable (low X, high Y) / High Risk (low-low)

6. **gs_risk_return** — Risk-Adjusted Return Analysis
   - X: "Downside Risk" — Burn multiple × Single-customer dependency × Regulatory cliff × Tech debt ratio (0-100, right = riskier)
   - Y: "Upside Potential" — Revenue multiple × Margin expansion room × TAM whitespace × Optionality value (0-100)
   - Zones: Sweet Spot (low risk, high return — top-left) / Avoid zone (high risk, low return — bottom-right)

7. **bubble_3d** — Innovation vs. Commercialization Bubble
   - X: "Innovation Velocity" — R&D-to-revenue ratio × OSS contribution × Research publication × Algorithmic breakthrough frequency (0-100)
   - Y: "Commercial Traction" — ARR growth × Net retention × Logo acquisition × Expansion revenue % (0-100)
   - Z (bubble size): "Market Presence" — Total funding raised × Enterprise logos × Geographic reach × Brand awareness (0-100)

### Data Structure
For EACH of the 6 markets, generate data for ALL 7 chart types.
Use **6 to 16 competitors** per market-chart (including the target, marked `is_target: true`).
- **Minimum 6 companies**: ensures meaningful cross-comparison across enough players
- **Maximum 16 companies**: prevents visual clutter while capturing the full competitive landscape
- Include a diverse mix: direct competitors, adjacent-market players, and emerging disruptors
- Competitor names may vary by market (use region-relevant players)

### Guidelines
- Use real, publicly known competitor names relevant to each market
- Axis values must be 0-100
- Provide localized titles and axis labels (EN + JA)
- Base positioning on publicly available data, analyst reports, and code/repo analysis
- The target company's position should be consistent across markets (reflecting its actual strength/weakness)
- This report will be reviewed by cross-functional teams (Engineering, Legal, Finance, Marketing, CISO). Ensure each chart provides insights relevant to multiple departments

Include the results in the `competitive_analysis` section of the JSON output.
"""

_COMPETITIVE_ANALYSIS_INSTRUCTIONS_JA = """## 競合分析タスク

対象企業について **固定6市場** にわたる包括的な競合分析を作成してください。
**5つのチャートタイプ** それぞれについて、全6市場のデータを生成します（1ページ = 2×3グリッド表示）。

### 固定6市場（この順番で必ず生成）
1. グローバル (Global)
2. 米国 (US)
3. EMEA
4. 日本 (Japan)
5. 東南アジア (SEA)
6. 中南米 (LATAM)

### 7つのチャートタイプ（各タイプが2×3グリッドで1ページ）

1. **magic_quadrant** — Forrester Wave / Gartner マジック・クアドラント
   - X: 「現行プロダクト力」— 機能網羅性 × API充実度 × ドキュメント品質 × エンタープライズ対応度 (0-100)
   - Y: 「戦略性」— ビジョン明確度 × ロードマップ野心度 × エコシステム構想 × 資金余力 (0-100)
   - 象限: リーダー(右上) / ストロングパフォーマー(右下) / コンテンダー(左上) / チャレンジャー(左下)

2. **bcg_matrix** — BCG 成長・シェアマトリックス
   - X: 「相対市場シェア(対数)」— 対#1収益比 × インストールベース × 開発者マインドシェア (0-100, 右=支配的)
   - Y: 「市場成長率」— TAM CAGR × 新セグメント創出力 × 地域拡大速度 (0-100)
   - 象限: スター(右上) / 問題児(左上) / 金のなる木(右下) / 負け犬(左下)

3. **mckinsey_moat** — McKinsey 9ボックス / 技術モートマトリックス
   - X: 「競争ポジション」— スイッチングコスト × データネットワーク効果 × 統合ロックイン × ブランドプレミアム (0-100)
   - Y: 「技術モート深度」— アルゴリズム独自性 × 独自データ × レイテンシ優位性 × モデルアーキテクチャ独自性 (0-100)
   - 象限: フォートレス(右上) / イノベーター(左上) / 既得権(右下) / コモディティ(左下)

4. **security_posture** — セキュリティ＆プライバシー成熟度マトリックス
   - X: 「セキュリティ実装深度」— 暗号化強度(保存時・通信時) × ゼロトラストアーキテクチャ採用度 × ペネトレーションテスト頻度 × インシデントレスポンス成熟度 (0-100)
   - Y: 「プライバシー＆コンプライアンス準備度」— GDPR/CCPA/HIPAA準拠レベル × データ最小化実践度 × 同意管理の洗練度 × プライバシーバイデザイン採用度 (0-100)
   - 象限: プライバシーリーダー(右上) / セキュリティ要塞(右下) / コンプライアンスリスク(左上) / 脆弱(左下)

5. **data_governance** — データガバナンス＆透明性マトリックス
   - X: 「データ保護能力」— E2E暗号化強度 × 鍵管理成熟度 × 情報漏洩対策(DLP) × アクセス制御粒度 × セキュア削除能力 (0-100)
   - Y: 「透明性＆説明責任」— 監査証跡の完全性 × データ処理の開示度 × 第三者監査頻度 × 侵害通知速度 × セキュリティコードOSS公開比率 (0-100)
   - 象限: 信頼リーダー(右上) / 不透明な要塞(右下) / 透明だが脆弱(左上) / 高リスク(左下)

6. **gs_risk_return** — リスク調整リターン分析
   - X: 「下振れリスク」— バーンマルチプル × 単一顧客依存度 × 規制クリフ × 技術的負債比率 (0-100, 右=リスク大)
   - Y: 「上振れポテンシャル」— レベニューマルチプル × マージン拡大余地 × TAM空白地帯 × オプション価値 (0-100)
   - ゾーン: スイートスポット（低リスク・高リターン＝左上）/ 回避ゾーン（高リスク・低リターン＝右下）

7. **bubble_3d** — イノベーション vs 商業化バブルチャート
   - X: 「イノベーション速度」— R&D対売上比率 × OSS貢献度 × 研究発表数 × アルゴリズム突破頻度 (0-100)
   - Y: 「商業トラクション」— ARR成長率 × ネットリテンション率 × ロゴ獲得数 × 拡張収益比率 (0-100)
   - Z (バブルサイズ): 「市場プレゼンス」— 累計調達額 × エンタープライズロゴ数 × 地域展開数 × ブランド認知度 (0-100)

### データ構造
6市場それぞれについて、**7つのチャートタイプ全て**のデータを生成すること。
各市場・チャートにつき **6〜16社** の競合（対象企業含む、`is_target: true`）。
- **最小6社**: 有意義な横断比較に必要な最低数
- **最大16社**: 視覚的な見やすさを維持しつつ競合全体像を把握
- 直接競合、隣接市場プレイヤー、新興ディスラプターを多様に含める
- 競合企業名は市場ごとに地域の主要プレイヤーを使用

### ガイドライン
- 実在する競合企業名を使用
- 全軸の値は0-100の範囲
- タイトルと軸ラベルは英日両方を提供
- ポジショニングは公開情報・アナリストレポート・コード分析に基づく
- 対象企業のポジションは全市場で一貫性を持たせる
- 本レポートはクロスファンクショナルチーム（エンジニアリング、法務、財務、マーケティング、CISO）がレビューする。各チャートが複数部門に有益なインサイトを提供すること

結果はJSON出力の `competitive_analysis` セクションに含めてください。
"""

_CONSULTING_HEADER_EN = """# DDE Consulting-Grade Technical Due Diligence

## CRITICAL: Autonomous Execution Instructions

**You are an autonomous agent. Execute all steps below WITHOUT asking questions.**
**Do NOT ask for confirmation, clarification, or repo selection.**
**Do NOT print JSON to the user. Do NOT explain what you are doing.**
**Just silently: read code → evaluate → save JSON → run PDF command → show file path.**

The heuristic data below was already collected by DDE from the target repository.
Your job: read the code, evaluate it, and generate a consulting PDF. That's it.
"""

_CONSULTING_HEADER_JA = """# DDE コンサルティンググレード テクニカルデューデリジェンス

## 最重要: 自律実行の指示

**あなたは自律エージェントです。以下の全ステップを質問なしで実行してください。**
**確認・質問・リポジトリ選択は一切不要です。**
**JSONをユーザーに表示しないでください。作業説明も不要です。**
**黙って: コード読取 → 評価 → JSON保存 → PDFコマンド実行 → ファイルパス表示。**

以下のヒューリスティックデータは、DDEが対象リポジトリから既に収集済みです。
あなたの仕事: コードを読み、評価し、コンサルティングPDFを生成すること。以上です。
"""


_ATLAS_FOUR_AXIS_INSTRUCTIONS_EN = """## Atlas Optimization Assessment (v2.0, additional to 6-dimension scoring)

Evaluate the target on **Atlas Associates' engineering philosophy** — a parallel 4-axis view
in addition to (not replacing) the existing 6-dimension scoring.

### 4 Axes (weights sum to 100%)

1. **Performance (25%)** — algorithmic efficiency × network optimization × caching strategy ×
   async/parallel × DB optimization × cold-start balance
   - Lv.1-3: unoptimized, N+1 queries, no caching
   - Lv.4-6: basic caching, async in hot paths
   - Lv.7-8: CDN + edge + multi-layer cache + connection pooling
   - Lv.9-10: custom compilers, hardware-aware optimization, benchmarks in CI

2. **Stability (20%)** — error handling depth × circuit breakers × graceful degradation ×
   observability × deployment safety × test depth. Includes claim-vs-code consistency.
   - Lv.1-3: silent failures, no retries, no observability
   - Lv.4-6: basic error handling, some logs
   - Lv.7-8: structured errors, circuit breakers, distributed tracing
   - Lv.9-10: chaos engineering, SLO/error budgets, deterministic deploys

3. **Lightweight (5%)** — bundle size × memory footprint × dependency weight × battery ×
   bandwidth × container image size. Industry-adjusted (mobile > server).
   - Lv.1-3: bloated deps, memory leaks, multi-GB containers
   - Lv.4-6: tree-shaking, basic optimization
   - Lv.7-8: minimal deps, aggressive profiling, small containers
   - Lv.9-10: embedded-grade optimization, custom allocators

4. **Security Strength (50% — THE CORE of Atlas philosophy)**

   Sub-breakdown (non-public weights, industry-adjusted, encryption-dominant):

   - **4a. Encryption Sophistication (30% of 50% = core)** — Signal Protocol, PQXDH, libsignal/BoringSSL
     - Lv.1-3: TLS only, MD5/SHA-1 usage
     - Lv.4-6: AES-GCM, SHA-256, basic key management
     - Lv.7-8: Signal Protocol adoption, XEdDSA, AEAD everywhere
     - Lv.9-10: PQXDH + ML-KEM-1024, Double Ratchet, NO self-rolled crypto, own research publications

   - **4b. Privacy Protection (8%)** — Evaluate the IMPLEMENTATION of privacy controls
     in code (data minimization, consent flow, deletion cascades, PII handling).
     GDPR/CCPA/HIPAA compliance _text_ is informational only — certifications and legal
     pages do NOT count toward this score; only the code behavior does.

   - **4c. Basic Hygiene (2% — MINIMAL)** — "anyone can add MFA, WebAuthn".
     Focus on the CODE implementation (auth flow, rate limiting, dep audit hooks).
     Third-party certifications (SOC2, ISO 27001, PCI-DSS) are **reference-only,
     not scored**. A company can be SOC2-certified with weak code; DDE ignores the
     badge and reads the code.

   - **4d. Communication Safety (7%)** — TLS 1.3 + Cert Pinning, Sealed Sender, mTLS, side-channel defense

   - **4e. Layer Composition (3%)** — defense-in-depth, VPC/subnet isolation, fail-secure defaults,
     at-rest + in-transit + in-use (TEE) encryption

### Weight Philosophy
Atlas believes **cryptographic IMPLEMENTATION sophistication (read from code) differentiates winners**
in privacy-conscious markets. Third-party certifications are **never scored**:
- A SOC2-certified plaintext-storage service still scores LOW on axis 4.
- An uncertified libsignal + PQXDH service still scores HIGH.
**We judge the code, not the badge.**

### Output JSON (inside main JSON root)

```json
"atlas_four_axis": {
  "axes": [
    {
      "axis_key": "performance",
      "name_en": "Performance", "name_ja": "高速化",
      "weight_pct": 25,
      "score": 0-100, "level": 1-10,
      "rationale": "...",
      "sub_items": []
    },
    {
      "axis_key": "stability",
      "name_en": "Stability", "name_ja": "安定化",
      "weight_pct": 20,
      "score": 0-100, "level": 1-10,
      "rationale": "...",
      "sub_items": []
    },
    {
      "axis_key": "lightweight",
      "name_en": "Lightweight", "name_ja": "軽量化",
      "weight_pct": 5,
      "score": 0-100, "level": 1-10,
      "rationale": "...",
      "sub_items": []
    },
    {
      "axis_key": "security",
      "name_en": "Security Strength", "name_ja": "セキュリティ強度",
      "weight_pct": 50,
      "score": 0-100, "level": 1-10,
      "rationale": "...",
      "sub_items": [
        {"key": "encryption", "name_en": "Cryptographic Sophistication", "name_ja": "暗号化技術の高度さ",
         "score": 0-100, "level": 1-10, "weight_pct": 30, "rationale": "..."},
        {"key": "privacy", "name_en": "Privacy Protection", "name_ja": "プライバシー保護",
         "score": 0-100, "level": 1-10, "weight_pct": 8, "rationale": "..."},
        {"key": "posture", "name_en": "General Security Posture", "name_ja": "一般セキュリティ態勢",
         "score": 0-100, "level": 1-10, "weight_pct": 2, "rationale": "..."},
        {"key": "comms", "name_en": "Communication Safety", "name_ja": "通信の安全",
         "score": 0-100, "level": 1-10, "weight_pct": 7, "rationale": "..."},
        {"key": "layers", "name_en": "Layer Composition", "name_ja": "レイヤー構成",
         "score": 0-100, "level": 1-10, "weight_pct": 3, "rationale": "..."}
      ]
    }
  ],
  "overall_score": 0-100,
  "industry_context": "messaging|fintech|medical|saas|gaming|iot|enterprise|other",
  "summary": "2-3 sentences on how the target aligns with Atlas philosophy",
  "summary_ja": "日本語版 2-3 文"
}
```

This is **additional** — the existing `dimension_scores` (6-dimension) must still be populated.
"""


_ATLAS_FOUR_AXIS_INSTRUCTIONS_JA = """## Atlas 最適化評価（v2.0、既存6次元スコアに追加）

対象企業を **Atlas Associates のエンジニアリング哲学** で評価してください。
これは既存6次元スコアに **置き換わる** ものではなく、**並列に追加される** 評価軸です。

### 4軸（重み合計100%）

1. **高速化 Performance (25%)** — アルゴリズム効率 × ネットワーク最適化 × キャッシュ戦略 ×
   非同期・並列 × DB最適化 × 起動時間
   - Lv.1-3: 未最適化、N+1問題、キャッシュなし
   - Lv.4-6: 基本キャッシュ、ホットパスで非同期
   - Lv.7-8: CDN + エッジ + 多層キャッシュ + コネクションプール
   - Lv.9-10: カスタムコンパイラ、ハードウェア最適化、CIでベンチマーク

2. **安定化 Stability (20%)** — エラー処理深度 × サーキットブレーカー × グレースフル劣化 ×
   可観測性 × デプロイ安全性 × テスト深度。主張整合性も含む。
   - Lv.1-3: 黙ったまま失敗、リトライなし、観測性ゼロ
   - Lv.4-6: 基本エラー処理、一部ログ
   - Lv.7-8: 構造化エラー、サーキットブレーカー、分散トレーシング
   - Lv.9-10: カオスエンジニアリング、SLO/エラーバジェット、決定論的デプロイ

3. **軽量化 Lightweight (5%)** — バンドルサイズ × メモリ × 依存関係 × バッテリー ×
   帯域幅 × コンテナイメージサイズ。業界調整（モバイル > サーバー）。
   - Lv.1-3: 肥大化、メモリリーク、数GBコンテナ
   - Lv.4-6: Tree-shaking、基本最適化
   - Lv.7-8: 最小依存、積極的プロファイリング
   - Lv.9-10: 組込級最適化、独自アロケータ

4. **セキュリティ強度 Security Strength (50% — Atlas 哲学の核心)**

   サブ内訳（非公開重み、業界別動的、暗号化主軸）:

   - **4a. 暗号化技術の高度さ（30%、核心）** — Signal Protocol、PQXDH、libsignal/BoringSSL
     - Lv.1-3: TLS のみ、MD5/SHA-1 使用
     - Lv.4-6: AES-GCM、SHA-256、基本鍵管理
     - Lv.7-8: Signal Protocol 採用、XEdDSA、AEAD 全面
     - Lv.9-10: PQXDH + ML-KEM-1024、Double Ratchet、**自前crypto実装なし**、独自暗号研究・論文

   - **4b. プライバシー保護（8%）** — コード内のプライバシー制御の **実装** を評価
     （データ最小化、同意フロー、削除カスケード、PII 扱い）。
     GDPR/CCPA/HIPAA の準拠 _文言_ は参考情報のみ。認証取得や法務ページは本スコアに
     **反映しない**（コードの実挙動のみ評価対象）。

   - **4c. 基本衛生（2% — 最小扱い）** — 「MFA、WebAuthn は誰でもできる」。
     **コード上の実装**（認証フロー、レート制限、依存監査フック）を評価。
     第三者認証（SOC2、ISO 27001、PCI-DSS）は **参考情報のみ、スコア対象外**。
     SOC2 を取得していてもコードが弱いことはあり得る。DDE はバッジを無視して
     コードを読む。

   - **4d. 通信の安全（7%）** — TLS 1.3 + Cert Pinning、Sealed Sender、mTLS、サイドチャネル対策

   - **4e. レイヤー構成（3%）** — 多層防御、VPC/サブネット分離、fail-secure デフォルト、
     at-rest + in-transit + in-use (TEE) 暗号化

### 重み哲学
Atlas は **プライバシー重視市場では暗号化の「実装」の高度さが勝者を分ける** と考えます。
第三者認証は **スコアに一切反映しない**:
- SOC2 取得済みでも平文保存のサービスは軸4で低評価（認証は関係ない）。
- SOC2 未取得でも libsignal + PQXDH + 自前crypto不在のサービスは高評価。
**判断対象はコード。認証バッジは参考情報のみ。**

### 出力 JSON（メイン JSON ルート内に配置）

（英語版と同構造。`name_ja`/`summary_ja` を必ず日本語で埋めること）

本評価は **追加** — 既存の `dimension_scores`（6次元）は必ず埋めてください。
"""


_IMPLEMENTATION_MATRIX_INSTRUCTIONS_EN = """## Implementation Capability Matrix (v2.0, 8th competitive chart)

Research the target + **exactly 5-10 top global competitors** (Series B+, established).
Mark each of ~30 items with implementation status for each company.

### 4-State Marking

- `"verified"` (✓): Publicly documented implementation (whitepaper, blog, GitHub, SOC2 report, pentest reports)
- `"claimed"` (△): Asserted in marketing/legal docs but not verifiable in code or audits
- `"not_implemented"` (✗): Explicitly absent (missing from stated scope)
- `"unknown"` (?): Cannot determine from public info — **prefer this over guessing**

### 30 Items (organized by axis category — research depth: minimum 3 sources per cell)

**Performance (3)**:
- `edge_caching` — CDN / edge compute / prefetching
- `async_parallel` — async/await, parallel execution
- `db_sharding` — DB partitioning, read replicas

**Stability (4)**:
- `circuit_breakers` — circuit breakers, bulkheads, retries with backoff
- `distributed_tracing` — OpenTelemetry, Jaeger, etc.
- `chaos_engineering` — chaos testing practices
- `slo_error_budget` — SLO tracking, error budget enforcement

**Lightweight (2)**:
- `tree_shaking` — bundle optimization
- `minimal_deps` — dependency audit, alternatives to heavy libs

**Encryption (11 — CORE DIFFERENTIATOR)**:
- `e2e_signal_protocol` — Signal Protocol / equivalent E2E
- `pqxdh_ml_kem` — PQXDH with ML-KEM-1024 (post-quantum)
- `double_ratchet` — Double Ratchet algorithm
- `xeddsa_ed25519` — XEdDSA / Ed25519 signatures
- `libsignal_boringssl_ffi` — uses libsignal or BoringSSL via FFI
- `no_self_rolled_crypto` — does NOT implement own crypto primitives
- `key_rotation` — automated key rotation
- `hsm_kms` — HSM or KMS for key management
- `forward_secrecy_pcs` — Forward Secrecy + Post-Compromise Security
- `zero_knowledge_proof` — ZK authentication or ZK data
- `crypto_research_publication` — published crypto research or conference talks

**Privacy (3)**:
- `gdpr_ccpa_implementation` — actual implementation, not just policy
- `data_minimization` — collect only what's needed
- `right_to_be_forgotten` — automated deletion cascade

**Basic Hygiene (2, minimal weight — code-based only)**:
- `mfa_webauthn` — multi-factor auth, WebAuthn (code-verified implementation)
- `soc2_iso27001` — SOC2 Type II or ISO 27001 (⚠ **reference only, not scored** —
  shown for reader context; do not let this item influence any score)

**Communications (3)**:
- `tls_1_3_pinning` — TLS 1.3, HSTS, Certificate Pinning
- `sealed_sender` — Sealed Sender / metadata minimization
- `mtls_inter_service` — mTLS for inter-service auth

**Layers (2)**:
- `defense_in_depth` — Network/App/Data layer defenses
- `confidential_computing` — TEE, SGX, SEV, AWS Nitro Enclaves

### Total: 30 items × (1 target + 5-10 competitors) columns

### Output JSON (inside main JSON root)

```json
"implementation_matrix": {
  "target_company": "Target Co",
  "competitors": ["Signal", "WhatsApp", "Telegram", "iMessage", "Wire"],
  "items": [
    {
      "category": "encryption",
      "item_key": "pqxdh_ml_kem",
      "item_en": "PQXDH / ML-KEM-1024",
      "item_ja": "PQXDH / ML-KEM-1024",
      "statuses": [
        {"company_name": "Target Co", "status": "verified", "evidence": "https://..."},
        {"company_name": "Signal", "status": "verified", "evidence": "https://signal.org/blog/..."},
        {"company_name": "WhatsApp", "status": "not_implemented", "evidence": "No public PQC announcement"},
        {"company_name": "Telegram", "status": "not_implemented", "evidence": "MTProto is not PQC"},
        {"company_name": "iMessage", "status": "verified", "evidence": "PQ3 since 2024"},
        {"company_name": "Wire", "status": "unknown", "evidence": "No public info"}
      ]
    }
  ]
}
```

Prefer `"unknown"` over guessing. False positives damage the report's credibility more than gaps.
"""


_IMPLEMENTATION_MATRIX_INSTRUCTIONS_JA = """## 実装能力マトリックス（v2.0、第8競合チャート）

対象企業 + **グローバルトップ企業 5〜10社**（Series B+、確立済み）を調査してください。
約30項目について各社の実装状況をマークします。

### 4状態マーキング

- `"verified"` (✓): 公開資料で実装確認済み（whitepaper、ブログ、GitHub、SOC2 報告、ペンテスト報告）
- `"claimed"` (△): マーケ/規約で主張あり、コード・監査で検証未完
- `"not_implemented"` (✗): 明示的に未対応（表明されたスコープに含まれない）
- `"unknown"` (?): 公開情報で判定不能 — **推測より不明を優先**

### 30項目（軸カテゴリ別、調査深度: 各セル最低3ソース）

**Performance（3）**: `edge_caching`, `async_parallel`, `db_sharding`

**Stability（4）**: `circuit_breakers`, `distributed_tracing`, `chaos_engineering`, `slo_error_budget`

**Lightweight（2）**: `tree_shaking`, `minimal_deps`

**Encryption（11 — 核心差別化領域）**:
`e2e_signal_protocol`, `pqxdh_ml_kem`, `double_ratchet`, `xeddsa_ed25519`,
`libsignal_boringssl_ffi`, `no_self_rolled_crypto`, `key_rotation`, `hsm_kms`,
`forward_secrecy_pcs`, `zero_knowledge_proof`, `crypto_research_publication`

**Privacy（3）**: `gdpr_ccpa_implementation`, `data_minimization`, `right_to_be_forgotten`

**基本衛生（2、最小重み・コードベース評価のみ）**:
- `mfa_webauthn` — 多要素認証・WebAuthn の **コード実装** を評価
- `soc2_iso27001` — SOC2 Type II / ISO 27001（⚠ **参考情報のみ・スコア対象外**。
  読者の文脈情報として表示するが、この項目はスコアに一切反映させないこと）

**Communications（3）**: `tls_1_3_pinning`, `sealed_sender`, `mtls_inter_service`

**Layers（2）**: `defense_in_depth`, `confidential_computing`

### 合計: 30項目 × （対象 + 5〜10社）列

出力 JSON は英語版と同構造。`item_ja` も必ず埋めてください。推測より `"unknown"` を優先。
"""


_COMPETITOR_RATIONALES_INSTRUCTIONS_EN = """## Competitor Selection Rationales (v0.3.1)

For EVERY competitor you included in `implementation_matrix.competitors`,
add an entry explaining **why this competitor was selected** — 3 to 5 lines each.

### CRITICAL — 1:1 Alignment Rule

The set of competitors MUST be **identical** across:
- `implementation_matrix.competitors` (the list)
- `implementation_matrix.items[*].statuses[*].company_name`
- `competitor_rationales[*].name`

**No mismatches allowed.** If a company appears in the matrix, it MUST appear in rationales.
If a company has a rationale, it MUST be in the matrix. The target company counts once
as `implementation_matrix.target_company` and does NOT need a rationale entry.

### Output JSON (top-level array)

```json
"competitor_rationales": [
  {
    "name": "Stripe",
    "category": "Direct competitor | Adjacent market | Emerging disruptor | Industry benchmark",
    "hq_country": "United States",
    "market_position": "Market leader / Challenger / Niche / Disruptor (1 line)",
    "rationale_en": "3-5 line explanation: why this company was chosen as a comparison target. Address: (1) what makes them comparable, (2) what they do differently, (3) why they matter for the target's strategic positioning.",
    "rationale_ja": "3-5 行で「なぜこの会社を比較対象に選んだか」を日本語で説明。 (1) 比較可能性の理由、(2) 対象との違い、(3) 戦略的ポジショニングへの関連性、を含める。",
    "estimated_score": 0-100
  }
]
```

### `estimated_score` Guidelines (0-100)

Provide a numeric estimate of the competitor's overall DD score based on
**publicly available information only**. Note:

- Public info (marketing pages, press releases, whitepapers) skews POSITIVE.
  The real score if we had source code access would likely be **LOWER**.
- Be conservative. When uncertain, estimate toward the middle (50-70 range).
- This number is a **rough public-info-based estimate**, not a verified score.
- The PDF will include a disclaimer to this effect — do not inflate optimism.

Cover every competitor that appears in the charts/matrix. Do NOT invent companies
you didn't analyze. Categories should be consistent across competitors.
"""

_COMPETITOR_RATIONALES_INSTRUCTIONS_JA = """## 競合選定理由（v0.3.1）

`implementation_matrix.competitors` に含めた **すべての競合企業**について、
**「なぜこの比較対象に選んだか」を 3〜5 行で説明**してください。

### 最重要 — 1:1 整合ルール

以下 3 箇所の競合企業セットは **完全一致** させること:
- `implementation_matrix.competitors`（リスト）
- `implementation_matrix.items[*].statuses[*].company_name`
- `competitor_rationales[*].name`

**不一致は禁止**。マトリックスに登場する会社は全て rationales にも記載すること。
rationale がある会社はマトリックスにも必ず含めること。対象企業本人は
`implementation_matrix.target_company` に 1 度登場し、rationales には含めない。

### 出力 JSON（トップレベル配列）

```json
"competitor_rationales": [
  {
    "name": "会社名",
    "category": "直接競合 | 隣接市場 | 新興ディスラプター | 業界ベンチマーク",
    "hq_country": "本社所在国",
    "market_position": "市場でのポジション（1 行）",
    "rationale_en": "3-5 line English explanation of why this competitor was chosen",
    "rationale_ja": "3〜5 行の日本語説明: (1) 比較可能性の理由、(2) 対象との違い、(3) 戦略的ポジショニングへの関連性",
    "estimated_score": 0-100
  }
]
```

### `estimated_score` ガイドライン（0-100 点）

各競合企業の DD 総合スコアを **公開情報のみに基づいて** 推定してください。注意事項:

- 公開情報（マーケページ・プレスリリース・ホワイトペーパー）は好意的に書かれがち。
  ソースコードにアクセスできた場合の実スコアは **より低くなる** 可能性が高い。
- 保守的に見積もる。不確実な場合は中央値（50-70）寄りに。
- この数値は **公開情報ベースの粗い推定** であり、検証済みスコアではない。
- PDF にその旨の注釈が自動で付くため、楽観的数値は避けること。

競合分析 / 実装マトリックスに登場する全企業をカバーすること。分析していない
企業を捏造しない。カテゴリ表記は全競合で一貫させる。
"""


_CONSULTING_EVAL_EN = """## Evaluation Task (execute silently — no user interaction)

Role: World-class technology consultant and senior software engineer.

## CRITICAL: Source Code Recency
**Always evaluate the LATEST source code state** (HEAD of the current branch,
uncommitted changes included if present in the working tree). Do NOT rely on
README descriptions, past impressions, or memory — read the actual files NOW.

## CRITICAL: AIDD (AI-Driven Development) Era Assumptions
- AI-assisted development is STANDARD in 2026. **Do NOT penalize AI usage** in any way.
- High-velocity commits (20+ commits in 24h, dense commit windows, rapid iteration)
  are NORMAL signals of AIDD. **Do NOT flag as suspicious**. **Do NOT reflect commit
  frequency/velocity in scoring** — neither positively nor negatively. It is informational only.
- Lean teams + AI leverage is the winning pattern. Headcount is NOT a quality signal.
- Evaluate CODE QUALITY, ARCHITECTURE, and TECHNICAL DEPTH — not developer count or commit cadence.

## CRITICAL: Source-Code-Only Evaluation (no cert credit)
DDE evaluates the target **purely from the source code**. Third-party certifications
(SOC2, ISO 27001, HIPAA, PCI-DSS, FedRAMP, Type I/II audits, penetration test certificates,
or any other audit badge) are **INFORMATIONAL ONLY** — they are listed for readers' reference
but **MUST NOT influence scoring** (positively or negatively):
- Do NOT add bonus points because SOC2 is held.
- Do NOT deduct points because it is absent.
- Present them in the Red Flags / Site Verification / rationale text where relevant,
  but always with a "reference-only, not scored" caveat.
- Rationale: certifications prove process, not code quality. DDE's job is to read
  the code. A SOC2-audited plaintext-storage service is still a plaintext-storage
  service. A startup without SOC2 but with libsignal + PQXDH is still cryptographically
  strong. We judge the code.

**Read all code in the repository**, then produce a JSON evaluation containing:

1. **5-Dimension Scoring** (1-10 scale, with rationale and what it enables)
   Dimensions (each 20%): technical_originality, technology_advancement, implementation_depth,
   architecture_quality (INCLUDING security posture — blend code structure + security maturity),
   claim_consistency. **Do NOT add a standalone "security_posture" key** — security is
   part of architecture_quality in v0.3.
2. **SWOT Analysis** — concrete, evidence-based
3. **Future Outlook** — product vision, viability, 1/3/5-year projections with confidence
4. **Strategic Advice** — immediate actions, medium-term priorities, long-term vision
5. **Investment Thesis** — recommendation with risks, upside, comparable companies
6. **Red Flag Re-evaluation** — correct heuristic false positives (esp. commit-velocity ones)
7. **Glossary Additions** — technical terms with plain-language definitions

Guidelines: Evidence-based. Cite file paths. No filler. Clear language. Include your model name.
"""

_CONSULTING_EVAL_JA = """## 評価タスク（黙って実行 — ユーザーとの対話なし）

役割: 世界トップクラスのテクノロジーコンサルタント兼シニアソフトウェアエンジニア。

## 最重要: 言語ルール
**JSONの全フィールドの値（executive_summary, rationale, SWOT points, explanations 等）は必ず日本語で記述すること。**
**英語で書かないでください。キー名はそのまま英語、値は全て日本語。**
**SWOT分析のpoint, explanation, business_analogy も全て日本語で書く。**

## 最重要: ソースコードの鮮度
**必ず最新のソースコード状態を評価すること**（現在のブランチの HEAD、
ワーキングツリーに未コミットの変更があればそれも含む）。README 記述や
過去の印象・記憶に依拠せず、**今その瞬間に実ファイルを読むこと**。

## 最重要: AIDD（AI駆動開発）前提
- 2026年時点で AI 支援開発は標準。**AI の使用に対して一切減点しない。**
- 高速コミット（24時間で20件以上、密集したコミット窓、高速イテレーション）は
  AIDD の正常シグナル。**「疑わしい」と扱わず、スコアリングにも反映しない**
  （加点も減点もしない、参考値のみ）。
- 少数精鋭 + AI レバレッジが勝ちパターン。人数は品質シグナルにならない。
- **コード品質・アーキテクチャ・技術的深度** を評価対象とする。開発者数や
  コミット頻度は評価対象外。

## 最重要: ソースコードのみで判断（第三者認証は参考情報扱い）
DDE は **純粋にソースコードのみから** 対象企業を評価する。第三者機関による認証
（SOC2、ISO 27001、HIPAA、PCI-DSS、FedRAMP、Type I/II 監査、ペネトレーションテスト証明書、
その他監査バッジ全般）は **参考情報として表示のみ** し、**スコアリングには一切反映しない**
（加点も減点もしない）:
- SOC2 取得済みでも加点しない。
- 未取得でも減点しない。
- レッドフラグ / サイト検証 / 根拠記述では関連箇所で言及 OK だが、
  必ず「参考情報・スコア対象外」の但し書きを併記すること。
- 理由: 認証はプロセスの証明であって、コード品質の証明ではない。DDE はコードを
  読むのが仕事。SOC2 監査済みの平文保存サービスは、依然として平文保存サービス。
  SOC2 未取得でも libsignal + PQXDH を使っているスタートアップは、依然として
  暗号学的に強い。**判断基準はコード**。

**リポジトリ内の全コードを読み取り**、以下を含むJSON評価を生成:

1. **5次元スコアリング**（各次元1-10、各20%重み、根拠と「何が可能になるか」付き）
   次元: technical_originality / technology_advancement / implementation_depth /
   architecture_quality（**セキュリティ態勢を内包** — コード構造 + セキュリティ成熟度を統合評価）/
   claim_consistency。**`security_posture` を独立キーとして追加しない**。v0.3 では
   architecture_quality にマージ済み。
2. **SWOT分析** — 具体的・エビデンスベース
3. **将来性評価** — ビジョン、実現可能性、1/3/5年予測（信頼度付き）
4. **戦略アドバイス** — 即座/中期/長期
5. **投資判断** — 推奨度＋根拠＋リスク/アップサイド＋類似企業
6. **レッドフラグ再評価** — 誤検知の修正（特に commit 速度系は全て無効化）
7. **追加用語集** — 技術用語の注釈

ガイドライン: エビデンスベース。ファイルパス引用。冗長さ排除。明確な言葉。モデル名を含める。
**繰り返し: JSON値は全て日本語で記述。英語で書いた場合PDFが不正になる。**
"""

_CONSULTING_JSON_SCHEMA = """## Output Format: JSON

Output your evaluation as a single JSON object with **exactly** this structure.
Do not add markdown formatting around it — output raw JSON only.

```json
{
  "project_name": "Target company or project name (used as report title and filename)",
  "executive_summary": "2-3 paragraph technical summary",
  "executive_summary_business": "2-3 paragraph non-technical summary for board/investors",
  "dimension_scores": {
    "technical_originality":  { "score": 0-100, "level": 1-10, "label": "e.g. Original, Extended, Frontier", "rationale": "evidence-based explanation", "business_explanation": "what this means in business terms", "enables": "what this capability makes possible" },
    "technology_advancement": { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" },
    "implementation_depth":   { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" },
    "architecture_quality":   { "score": 0-100, "level": 1-10, "label": "incl. Security Posture", "rationale": "blend architecture + security maturity", "business_explanation": "", "enables": "" },
    "claim_consistency":      { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" }
  },
  "overall_score": 0-100,
  "grade": "A|B|C|D|F",
  "swot": {
    "strengths": [
      { "point": "title", "explanation": "detail", "business_analogy": "real-world comparison" }
    ],
    "weaknesses": [
      { "point": "title", "explanation": "detail", "business_impact": "consequence" }
    ],
    "opportunities": [
      { "point": "title", "explanation": "detail", "potential_value": "upside" }
    ],
    "threats": [
      { "point": "title", "explanation": "detail", "mitigation": "how to address" }
    ]
  },
  "future_outlook": {
    "product_vision": "what this product/service is trying to achieve",
    "viability_assessment": "can they pull it off? why or why not?",
    "year_1": { "projection": "...", "confidence": "high|medium|low", "key_milestones": ["..."] },
    "year_3": { "projection": "...", "confidence": "high|medium|low", "key_milestones": ["..."] },
    "year_5": { "projection": "...", "confidence": "high|medium|low", "key_milestones": ["..."] }
  },
  "strategic_advice": {
    "immediate_actions": [
      { "action": "what to do", "rationale": "why", "expected_impact": "outcome" }
    ],
    "medium_term": [
      { "action": "what to do", "rationale": "why", "expected_impact": "outcome" }
    ],
    "long_term_vision": "where this should be heading"
  },
  "investment_thesis": {
    "recommendation": "strong_invest|invest_with_conditions|cautious|pass|strong_pass",
    "rationale": "3-5 sentences explaining the recommendation",
    "key_risks": ["risk 1", "risk 2"],
    "key_upside": ["upside 1", "upside 2"],
    "comparable_companies": ["company 1", "company 2"],
    "suggested_valuation_factors": "what affects valuation"
  },
  "red_flags": [
    { "title": "flag title", "description": "detail", "severity": "critical|high|medium|low", "business_impact": "impact" }
  ],
  "tech_level_summary": {
    "overall_level": 1-10,
    "overall_label": "e.g. Production-Grade",
    "plain_explanation": "what this level means in everyday terms"
  },
  "glossary_additions": [
    { "term": "technical term", "definition": "plain-language explanation" }
  ],
  "ai_model_used": "your model name (e.g. Claude Sonnet 4, GPT-4o, etc.)",
  "site_verification": {
    "urls_analyzed": ["https://example.com", "..."],
    "items": [
      {
        "item_key": "feature_claim_match",
        "item_name": "Feature Claim Match",
        "item_name_ja": "機能主張一致度",
        "score": 0-100,
        "confidence": "high|medium|low",
        "rationale": "evidence-based explanation",
        "evidence": ["URL or file path 1", "..."]
      }
    ],
    "overall_credibility": 0-100,
    "summary": "overall credibility assessment paragraph"
  },
  "competitive_analysis": {
    "target_company": "company name",
    "home_country": "e.g. Japan",
    "markets": [
      {
        "market_name": "Global",
        "market_name_ja": "グローバル",
        "charts": [
          {
            "chart_type": "magic_quadrant|bcg_matrix|mckinsey_moat|security_posture|data_governance|gs_risk_return|bubble_3d",
            "title": "Chart Title",
            "title_ja": "チャートタイトル",
            "x_axis_label": "X Axis",
            "x_axis_label_ja": "X軸",
            "y_axis_label": "Y Axis",
            "y_axis_label_ja": "Y軸",
            "x_axis_rationale": "Why this X axis matters and what it measures (1-2 sentences, EN)",
            "x_axis_rationale_ja": "X軸の選定理由と測定内容（1-2文、日本語）",
            "y_axis_rationale": "Why this Y axis matters and what it measures (1-2 sentences, EN)",
            "y_axis_rationale_ja": "Y軸の選定理由と測定内容（1-2文、日本語）",
            "data_points": [
              { "name": "Company A", "x": 0-100, "y": 0-100, "z": 0-100, "is_target": false },
              { "name": "Target Co", "x": 0-100, "y": 0-100, "z": 0-100, "is_target": true }
            ]
          }
        ]
      }
    ]
  },
  "atlas_four_axis": {
    "axes": [
      {"axis_key": "performance",  "name_en": "Performance",          "name_ja": "高速化",                "weight_pct": 25, "score": 0-100, "level": 1-10, "rationale": "...", "sub_items": []},
      {"axis_key": "stability",    "name_en": "Stability",            "name_ja": "安定化",                "weight_pct": 20, "score": 0-100, "level": 1-10, "rationale": "...", "sub_items": []},
      {"axis_key": "lightweight",  "name_en": "Lightweight",          "name_ja": "軽量化",                "weight_pct":  5, "score": 0-100, "level": 1-10, "rationale": "...", "sub_items": []},
      {"axis_key": "security",     "name_en": "Security Strength",  "name_ja": "セキュリティ強度", "weight_pct": 50, "score": 0-100, "level": 1-10, "rationale": "...",
        "sub_items": [
          {"key": "encryption", "name_en": "Cryptographic Sophistication", "name_ja": "暗号化技術の高度さ", "weight_pct": 30, "score": 0-100, "level": 1-10, "rationale": "..."},
          {"key": "privacy",    "name_en": "Privacy Protection",            "name_ja": "プライバシー保護",     "weight_pct":  8, "score": 0-100, "level": 1-10, "rationale": "..."},
          {"key": "posture",    "name_en": "General Security Posture",      "name_ja": "一般セキュリティ態勢", "weight_pct":  2, "score": 0-100, "level": 1-10, "rationale": "..."},
          {"key": "comms",      "name_en": "Communication Safety",          "name_ja": "通信の安全",           "weight_pct":  7, "score": 0-100, "level": 1-10, "rationale": "..."},
          {"key": "layers",     "name_en": "Layer Composition",             "name_ja": "レイヤー構成",         "weight_pct":  3, "score": 0-100, "level": 1-10, "rationale": "..."}
        ]
      }
    ],
    "overall_score": 0-100,
    "industry_context": "messaging|fintech|medical|saas|gaming|iot|enterprise|other",
    "summary": "2-3 sentences on Atlas philosophy alignment",
    "summary_ja": "日本語版 2-3 文"
  },
  "implementation_matrix": {
    "target_company": "Target Co",
    "competitors": ["CompetitorA", "CompetitorB", "..."],
    "items": [
      {
        "category": "encryption",
        "item_key": "pqxdh_ml_kem",
        "item_en": "PQXDH / ML-KEM-1024",
        "item_ja": "PQXDH / ML-KEM-1024",
        "statuses": [
          {"company_name": "Target Co",   "status": "verified|claimed|not_implemented|unknown", "evidence": "URL or citation"},
          {"company_name": "CompetitorA", "status": "verified|claimed|not_implemented|unknown", "evidence": "..."}
        ]
      }
    ]
  },
  "competitor_rationales": [
    {
      "name": "CompetitorA",
      "category": "Direct competitor|Adjacent market|Emerging disruptor|Industry benchmark",
      "hq_country": "United States",
      "market_position": "one-line positioning",
      "rationale_en": "3-5 line English explanation",
      "rationale_ja": "3〜5 行の日本語説明",
      "estimated_score": 0-100
    }
  ]
}
```

**IMPORTANT**:
- `project_name` is **required** — use the target company/project name (e.g. "Arc Messenger", "Stripe", "OpenAI"). This is used as the PDF report title and filename
- If no URLs were provided for site verification, set `"site_verification": null`
- The `competitive_analysis` section is **always required** — never set it to null
- The `atlas_four_axis` section is **always required** (v2.0) — exactly 4 axes (performance/stability/lightweight/security), `security` axis must include 5 sub_items with the exact keys (encryption/privacy/posture/comms/layers)
- The `implementation_matrix` section is **always required** (v2.0) — 5-10 competitors + target, ~30 items across 8 categories. Prefer `"unknown"` over guessing
- The `competitor_rationales` array is **always required** (v0.3.1) — MUST contain one entry per company in `implementation_matrix.competitors` (exact 1:1 match by name). Target company is NOT in rationales. NO mismatches allowed.
- For each chart, `x_axis_rationale` / `y_axis_rationale` (and their `_ja` variants) are **required** — explain why this axis was chosen and what the composite score captures. This helps cross-functional readers (non-engineers, legal, finance) understand the chart
- For `site_verification.items`, include all 9 items (feature_claim_match, tech_stack_consistency, security_claim_verification, performance_claim_plausibility, scale_claim_consistency, launch_date_verification, pricing_feasibility, compliance_display, ai_washing_index). **Team size estimation is INTENTIONALLY excluded — AI era = lean teams + AI leverage, headcount is not a quality signal**
- For `competitive_analysis.markets`, include all 6 markets (Global, Home Country, US, EMEA, SEA, LATAM) with all 7 chart types specified in the Competitive Analysis Task section
"""


def _consulting_pdf_command(result: AnalysisResult, lang: str) -> str:
    """Generate the final instruction to save JSON and produce PDF."""
    from datetime import datetime

    project_safe = result.project_name.replace("/", "_").replace("\\", "_")
    date_stamp = datetime.now().strftime("%Y%m%d")
    filename = f"dde_consulting_{project_safe}_{date_stamp}.json"

    if lang == "ja":
        return f"""## 実行手順（質問せずに全て実行すること）

**Step 1**: リポジトリのコードを読み取り、上記スキーマに従ったJSONを生成する
**Step 2**: JSONを `/tmp/{filename}` に保存する（Write toolまたはcatコマンドで）
**Step 3**: 以下のコマンドを実行する:

```bash
dde report --consulting /tmp/{filename} --pdf --lang ja
```

**Step 4**: PDFは `~/Downloads/` に保存される。ファイルパスをユーザーに伝える

**禁止事項:**
- JSONの内容をユーザーに表示しない
- 「どのリポジトリを分析しますか」等の質問をしない
- 作業の途中経過を説明しない
- 実行前に許可を求めない（ツール実行の同意のみ必要）
"""
    else:
        return f"""## Execution Steps (do NOT ask questions — just execute)

**Step 1**: Read the repository code and generate JSON following the schema above
**Step 2**: Save JSON to `/tmp/{filename}` (via Write tool or cat command)
**Step 3**: Run this command:

```bash
dde report --consulting /tmp/{filename} --pdf --lang en
```

**Step 4**: PDF is saved to `~/Downloads/`. Tell the user the file path.

**Do NOT:**
- Print the JSON to the user
- Ask "which repository?" or any clarification questions
- Explain what you are doing step by step
- Ask for permission before executing (only tool approval is needed)
"""
