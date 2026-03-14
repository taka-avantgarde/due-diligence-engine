<div align="center">

# Due Diligence Engine

**AI駆動型テクニカル・デューデリジェンス for ベンチャーキャピタル**

スタートアップの技術的主張を検証。AIウォッシュを検出。確信を持ってスコアリング。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Claude](https://img.shields.io/badge/AI-Claude_Opus_4.6-orange.svg)](https://anthropic.com)

[English](README.md) | [日本語](README.ja.md)

</div>

---

## これは何？

**Due Diligence Engine** は、VCや投資家がNDA締結後にスタートアップの技術的主張を検証するためのCLI + Webツールです。GitHub OAuthでPrivateリポジトリに一時的にアクセスし、Claude Opus 4.6でソースコードを分析、スコア付きレポートを生成した後、**ワンクリックでアクセス解除 + データ完全破棄**を実行します。

### 課題

- スタートアップが「独自AI」と主張 — 実はGPTのラッパーでは？
- 技術デューデリジェンスは数週間、コンサル費用は数百万円
- 技術バックグラウンドのない投資家は工学的主張を検証できない
- NDA保護下の資料は厳格なデータ管理が必要

### 解決策

```
接続 → 分析 → スコアリング → レポート → 切断 & 破棄
 1分    10分     自動          自動       ワンクリック
```

所要時間: **約15分**。従来のTech DDの数週間と比較してください。

---

## URLを入れるだけ

```bash
dde analyze https://github.com/some-startup/their-product
```

これだけです。ワンコマンドで技術デューデリジェンス完了。

### VCの方へ

```
Step 1: スタートアップのGitHubリポジトリURLをもらう
Step 2: dde analyze <URL>
Step 3: スコアカードを確認
```

### スタートアップの方へ（技術力を証明する）

このファイルをリポジトリに追加するだけ — VCがいつでもDDを実行できます：

```yaml
# .github/workflows/dde.yml
name: Technical Due Diligence
on: workflow_dispatch
jobs:
  dd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: taka-avantgarde/due-diligence-engine@main
        with:
          skip_ai: 'true'
```

VCがスタートアップのリポジトリで **「Run workflow」** をクリック → 即座にDDレポートが生成されます。

---

## 機能一覧

| 機能 | 説明 |
|------|------|
| **GitHub Private Repo連携** | OAuth連携でスタートアップがPrivateリポジトリへの一時アクセスを許可 |
| **コード実在性チェック** | AST解析でAIロジックがコードベースに実在するか検証 |
| **AIウォッシュ検出** | 「独自AI」と偽るAPIラッパーを検出 |
| **Git履歴フォレンジック** | コミット履歴の不審パターンを分析（DD直前の急造など） |
| **文書-コード整合性** | 技術文書の主張と実装の乖離を検出 |
| **アーキテクチャ可視化** | 実際のシステム構成をMermaid図で自動生成 |
| **100点満点スコアリング** | 6軸の加重スコアリング + RED FLAG自動検出 |
| **PDF出力** | 投資委員会向けプロフェッショナルPDFレポート |
| **切断 & 破棄ボタン** | ワンクリックでGitHub切断 + データ暗号消去 + 破棄証明書発行 |
| **Webダッシュボード** | 非技術系VC向けブラウザベースUI |

---

## スコアリングフレームワーク

```
┌─────────────────────────────────────────────┐
│            評価軸                             │
├─────────────────────────────────────────────┤
│  技術実在性          ████████░░  /25         │
│  独自性              ████████░░  /20         │
│  スケーラビリティ     ████████░░  /15         │
│  チーム実装力        ████████░░  /15         │
│  セキュリティ        ████████░░  /10         │
│  ビジネス整合性      ████████░░  /15         │
├─────────────────────────────────────────────┤
│  合計                            /100        │
│                                             │
│  90-100  ✅ STRONG    — 卓越した技術基盤     │
│  80-89   ✅ SOLID     — 投資検討に値する      │
│  60-79   ⚠️ CAUTION  — 要確認事項あり        │
│  40-59   🔴 CONCERN  — 重大な懸念あり        │
│  0-39    🔴 CRITICAL — 致命的な問題あり       │
└─────────────────────────────────────────────┘
```

---

## クイックスタート

### 前提条件

- Python 3.11+
- Anthropic APIキー（Claude Opus 4.6）
- GitHub OAuth App（Privateリポジトリアクセス用）

### インストール

```bash
git clone https://github.com/taka-avantgarde/due-diligence-engine.git
cd due-diligence-engine
pip install -e .
```

### 設定

```bash
export ANTHROPIC_API_KEY="your-api-key"

# オプション: Webダッシュボードでの Private Repo アクセス用
export GITHUB_CLIENT_ID="your-github-oauth-app-id"
export GITHUB_CLIENT_SECRET="your-github-oauth-app-secret"
```

### 使い方 — CLI

```bash
# GitHub URLを貼るだけで分析開始！
dde analyze https://github.com/some-startup/their-repo

# 短縮形（owner/repo）
dde analyze some-startup/their-repo

# 特定ブランチを指定
dde analyze https://github.com/some-startup/their-repo/tree/develop

# ローカルディレクトリ
dde analyze /path/to/startup-code

# Zipアーカイブ
dde analyze /path/to/startup-code.zip

# オプション付き
dde analyze some-startup/repo --name "Startup X" --format html --format md

# AIなし（ローカル解析のみ、無料）
dde analyze some-startup/repo --skip-ai

# リーダーボードを表示（80点以上のみ）
dde leaderboard
```

### 使い方 — Webダッシュボード（Private Repo対応）

```bash
# Webサーバーを起動
dde serve

# ブラウザで http://localhost:8000/dashboard/ を開く
```

Webダッシュボードの機能:
1. **Connect with GitHub** — OAuthフローでスタートアップのPrivateリポジトリにアクセス
2. **リポジトリ選択 & 分析** — 対象リポジトリを選んで分析実行
3. **結果閲覧** — スコアカード、RED FLAGS、アーキテクチャ図
4. **PDF出力** — 投資委員会向けレポートをダウンロード
5. **切断 & 破棄** — アクセス解除 + データ暗号消去

---

## 動作フロー

```
                    ┌──────────────────┐
                    │  GitHub Private  │
                    │  Repo (OAuth経由) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  1. 取込         │
                    │  Shallow clone   │
                    │  暗号化ストア     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────────┐ ┌───▼──────────┐
     │ コード解析     │ │ 文書精査   │ │ Git調査      │
     │ AST/依存関係/  │ │ 主張 vs    │ │ コミット     │
     │ API検出        │ │ 実態       │ │ パターン     │
     └────────┬───────┘ └───┬────────┘ └───┬──────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼─────────┐
                    │ 2. 分析          │
                    │ Haiku → Sonnet   │
                    │ → Opus（ハイブリッド）│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ 3. スコアリング   │
                    │ 100点満点        │
                    │ RED FLAG検出     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────────┐ ┌───▼──────────┐
     │ 4. レポート     │ │ 5. PDF     │ │ 6. 破棄      │
     │ MD / HTML      │ │ 出力       │ │ 切断         │
     │ スライド        │ │（コードなし）│ │ + 暗号消去   │
     └────────────────┘ └────────────┘ │ + 破棄証明書  │
                                       └──────────────┘
```

---

## Private Repoワークフロー（VC ↔ スタートアップ）

```
Step 1: VCがスタートアップにアクセス許可リンクを送付
Step 2: スタートアップがGitHub OAuthを承認（リポジトリアクセスを許可）
Step 3: DDEが暗号化一時ディレクトリにリポジトリをクローン
Step 4: 分析実行（Haiku → Sonnet → Opus）
Step 5: VCがスコアカードを確認 + PDFをダウンロード
Step 6: VCが「切断 & 破棄」をクリック
         ├─ GitHubトークンを無効化
         ├─ 全ソースコードを暗号消去
         ├─ 破棄証明書を発行
         └─ スコアと所見のみ保持（コードなし）
```

---

## 出力例

### スコアカード

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 企業名:   [非公開]
 日付:     2026-03-14
 総合:     62 / 100  ⚠️ 要注意
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 技術実在性        ████████░░  16/25
 独自性            ███░░░░░░░   6/20
 スケーラビリティ   ████████░░  12/15
 チーム実装力      ██████░░░░  12/15
 セキュリティ      ████████░░   8/10
 ビジネス整合性    ████░░░░░░   8/15
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🔴 RED FLAGS:
 ・「独自LLM」と主張 — コード上はOpenAI API の
   薄いラッパー（最小限のプロンプト工学のみ）
 ・Gitコミットの80%が直近2週間に集中
   （DD直前の急造開発の疑い）
 ・コアMLパイプラインのテストカバレッジなし
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### PDFレポート

カバーページ、スコア内訳、RED FLAGS、アーキテクチャ所見、NDAフッター付きのプロフェッショナルPDF。**ソースコードは一切含まれません** — 分析所見と推奨事項のみ。

### 切断 & 破棄 確認

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 破棄証明書
 証明書ID:     dde_purge_a1b2c3d4
 日時:         2026-03-14T15:30:00Z
 削除ファイル: 847件
 消去バイト:   12,345,678
 消去方式:     3パスランダム上書き
 GitHubトークン: 無効化済み
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## データセキュリティ & NDA遵守

| 保証事項 | 実装方法 |
|---------|---------|
| **クラウド保存なし** | 全データはローカルの暗号化tmpfsで処理 |
| **OAuthトークン暗号化** | Fernet暗号化、インメモリのみ（ディスク保存なし） |
| **API送信時の保護** | Anthropic 0-day retention policy を活用 |
| **暗号消去** | 3パスランダム上書き + 暗号化ボリューム破壊 |
| **破棄証明書** | SHA-256署名付き証明書でデータの存在と破棄を証明 |
| **GitHub切断** | 切断時にGitHub APIでOAuthトークンを無効化 |
| **レポートに生コードなし** | PDF/MDレポートには所見のみ、ソースコードは含まない |
| **監査証跡** | 全操作のタイムスタンプ付きログで監査対応 |

---

## プロジェクト構成

```
due-diligence-engine/
├── src/
│   ├── ingest/              # セキュア・データ取込（ローカル、zip、GitHub URL）
│   ├── analyze/             # Claude駆動分析
│   │   ├── code.py          # AST・依存関係解析
│   │   ├── docs.py          # 文書主張抽出
│   │   ├── git_forensics.py # Git履歴フォレンジック
│   │   ├── consistency.py   # 整合性チェッカー
│   │   └── engine.py        # ハイブリッドモデル・オーケストレーター
│   ├── score/               # 100点スコアリングエンジン
│   ├── report/
│   │   ├── generator.py     # MD/HTMLレポート生成
│   │   ├── slides.py        # アーキテクチャ可視化
│   │   └── pdf_generator.py # プロフェッショナルPDF出力
│   ├── purge/               # 暗号データ破棄
│   ├── saas/
│   │   ├── app.py           # FastAPIエンドポイント
│   │   ├── dashboard.py     # WebダッシュボードUI
│   │   ├── github_oauth.py  # GitHub OAuth連携
│   │   ├── billing.py       # Stripe課金（2倍料金）
│   │   └── auth.py          # APIキー認証
│   └── cli.py               # CLIインターフェース
├── templates/
│   ├── evaluation.md        # 評価フレームワーク
│   ├── scorecard.html       # スコアカードテンプレート
│   └── dashboard.html       # Webダッシュボードテンプレート
├── pyproject.toml
└── README.md
```

---

## デプロイオプション

### オプション1: セルフホスト CLI（OSS / 無料）

ご自身のAnthropic APIキーを使用。完全なデータ制御、API呼び出し以外のデータ送信なし。

```bash
pip install due-diligence-engine
export ANTHROPIC_API_KEY="sk-..."
dde analyze owner/repo
```

### オプション2: セルフホスト Webダッシュボード（OSS / 無料）

GitHub OAuthでPrivate Repoアクセス可能なWebダッシュボードをローカル実行。

```bash
export ANTHROPIC_API_KEY="sk-..."
export GITHUB_CLIENT_ID="..."
export GITHUB_CLIENT_SECRET="..."
dde serve
# ブラウザで http://localhost:8000/dashboard/ を開く
```

### オプション3: SaaS API（マネージドサービス）

APIキーやインフラ管理を避けたいVC向け。**料金: APIコスト x 2倍**（透明なマークアップ）。

#### SaaS料金表

| プラン | 月額基本料 | 分析あたり | 上限 | 機能 |
|--------|-----------|-----------|------|------|
| **Starter** | - | APIコスト x 2（最低$0.50） | 5件/月 | スコア + 基本レポート |
| **Professional** | - | APIコスト x 2（最低$0.50） | 25件/月 | + スライド + PDF + Git調査 |
| **Enterprise** | 要相談 | APIコスト x 2 | 無制限 | + 破棄証明書 + 優先サポート |

#### コスト例（1回の分析あたり）

```
10,000行コードベースのハイブリッド分析:

  Haiku  (スキャン) →  $0.50 APIコスト  →  $1.00 請求
  Sonnet (分析)     →  $4.00 APIコスト  →  $8.00 請求
  Opus   (判定)     →  $7.00 APIコスト  →  $14.00 請求
  ──────────────────────────────────────────────────
  合計                $11.50 APIコスト  →  $23.00 請求
```

---

## ロードマップ

- [x] コア評価フレームワーク設計
- [x] セキュア取込パイプライン付きCLIツール
- [x] Claude Opus 4.6 ハイブリッド統合（Haiku → Sonnet → Opus）
- [x] コード解析エンジン（AST + 依存関係グラフ）
- [x] Gitフォレンジックモジュール
- [x] RED FLAG検出付きスコアリングエンジン
- [x] Stripe課金付きSaaS API（2倍料金）
- [x] GitHub URL直接分析（`dde analyze owner/repo`）
- [x] GitHub OAuthによるPrivate Repoアクセス
- [x] Webダッシュボード（接続→分析→切断フロー）
- [x] PDFレポート出力（ソースコード含まず）
- [x] 切断 & 破棄 + 破棄証明書発行
- [ ] リーダーボード管理
- [ ] バッチ分析モード（ポートフォリオ一括DD）
- [ ] スタートアップ側アクセス承認ポータル

---

## 免責事項

本ツールは**投資判断を支援するための技術分析**を提供します。投資助言ではありません。スコアは提供された資料の自動分析に基づくものであり、デューデリジェンスプロセスにおける複数のインプットの一つとしてご利用ください。投資判断には必ず専門家にご相談ください。

---

## ライセンス

[Apache License 2.0](LICENSE) — 詳細は [LICENSE](LICENSE) をご参照ください。

---

<div align="center">

**[Claude Opus 4.6](https://anthropic.com) by Anthropic で構築**

</div>
