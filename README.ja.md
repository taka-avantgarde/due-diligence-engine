<div align="center">

# 🔍 Due Diligence Engine

### **IDE の AI が、世界トップクラスの技術DDアナリストになる**

<sub>**APIキー不要 · PDF出力 · OSS · CodeQL監査済み**</sub>

<br/>

```
┌─────────────────────────────────────────────────────────────┐
│  $ dde prompt --pdf --lang ja                               │
│                                                             │
│  コードベースを読み取り...                                    │
│  6次元で評価...                                              │
│  競合ランドスケープ構築（7チャート×6市場）...                │
│  実装能力マトリックス調査（30項目×10社）...                  │
│                                                             │
│  スコア: [■■■■■■■■■■■■■■■■■■■■■■■■■■□□□□] 82/100 Lv.8     │
│  グレード: B  →  条件付きで投資可能                           │
│                                                             │
│  → ~/Downloads/dde_consulting_<project>_<date>.pdf  (22 p.) │
└─────────────────────────────────────────────────────────────┘
```

<br/>

[![License](https://img.shields.io/badge/License-Apache_2.0-000000.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-5271FF.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![CodeQL](https://img.shields.io/badge/Security-CodeQL_·_Dependabot_·_pip--audit-5271FF.svg?style=for-the-badge&logo=github&logoColor=white)](SECURITY.md)
[![PDF](https://img.shields.io/badge/Output-PDF_First-000000.svg?style=for-the-badge&logo=adobeacrobatreader&logoColor=white)](#)

[English](README.md) · [**日本語**](README.ja.md)

</div>

---

## ⚡ クイックスタート

```bash
pip install --no-cache-dir git+https://github.com/taka-avantgarde/Due-diligence-engine.git
dde prompt --pdf --lang ja
```

AI 搭載 IDE のターミナル（Claude Code / Cursor / Copilot 等）で実行するだけ。
AI がコードベースを読み、世界トップクラスのテクノロジーコンサルタントとして評価し、
22ページの PDF を `~/Downloads/` に書き出します。**APIキー不要・クラウド経由なし・追加コスト¥0。**

---

## DDE の差別化ポイント

ありがちな「AIコードレビュアー」のチェック:
> *「認証あるか？✓ HTTPS あるか？✓ テストあるか？✓」*

これはチェックリスト遵守。**DDE はもっと深く掘ります:**

> *「暗号化は Signal Protocol か？ PQXDH + ML-KEM-1024 か？
> libsignal/BoringSSL FFI か、それとも自前 crypto 実装か？
> チームは暗号研究を発表しているか？」*

土台は **Atlas エンジニアリング哲学**: 暗号技術の高度さと深い技術独自性が勝者を分ける。
チェックリスト遵守（SOC2、MFA、WebAuthn）は最低限の衛生であり、差別化要因ではない。

---

## 🔒 Atlas エンジニアリング哲学（v2.0 — 暗号化主軸）

既存6次元スコアに **置き換わるのではなく並列に追加** される評価系。

```
4軸 — 重み合計 100%

  高速化            25%  ████████████░░░░░░░░░░░░░░░░░░░░
  安定化            20%  ██████████░░░░░░░░░░░░░░░░░░░░░░
  軽量化             5%  ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  超高度セキュリティ 50%  █████████████████████████░░░░░░░  ← 核心

  セキュリティのサブ内訳（50% 中の重み）:
    暗号化技術の高度さ          30%  ← Signal Protocol、PQXDH、libsignal
    プライバシー保護              8%
    通信の安全                    7%
    レイヤー構成                  3%
    一般セキュリティ態勢          2%  ← MFA、SOC2 等は最小衛生
```

---

## 📊 6次元標準スコア（v1.x — 完全保持）

| 評価軸 | 重み | 検出内容 |
|--------|----:|---------|
| 技術独自性 | 25% | API ラッパー vs 本物の IP |
| 技術先進性 | 20% | 技術スタックの先進度 |
| 実装深度 | 20% | PoC vs 本番品質 |
| アーキテクチャ品質 | 15% | 設計品質 |
| 主張整合性 | 10% | ピッチ vs 現実 |
| セキュリティ態勢 | 10% | セキュリティ成熟度 |

```
グレード分類:

  0      40       60      75       90     100
  |------|--------|-------|--------|------|
   F      D        C       B        A
   ✗      ⚠        ⚡       ✓        ★
```

| グレード | 推奨アクション |
|---------|----------------|
| ★ A (90+)  | 有力な投資候補 |
| ✓ B (75-89)| 条件付きで投資可能 |
| ⚡ C (60-74)| 重要な懸念あり |
| ⚠ D (40-59) | 高リスク |
| ✗ F (<40)  | 投資不可 |

各軸は **Lv.1〜10** でも明確な基準付きで評価。

---

## 🎯 競合分析チャート 7種 × 6市場

6つのグローバル市場（グローバル / 米国 / EMEA / 日本 / SEA / 中南米）それぞれで:

| # | チャート | 評価軸 |
|---|---------|--------|
| 1 | **Forrester Wave / マジック・クアドラント** | ビジョン × 実行力 |
| 2 | **BCG 成長・シェアマトリックス** | 市場成長率 × 相対シェア |
| 3 | **McKinsey 技術モート** | 競争ポジション × 技術モート深度 |
| 4 | **セキュリティ＆プライバシー成熟度** | セキュリティ実装 × プライバシー準備 |
| 5 | **データガバナンス＆透明性** | データ保護 × 監査透明性 |
| 6 | **GS リスク調整リターン** | 下振れリスク × 上振れポテンシャル |
| 7 | **イノベーション vs 商業化** | R&D 速度 × ARR トラクション (3D バブル) |

各チャートに **6〜16社** の競合を配置。**軸選定理由キャプション** で
*なぜ* この軸か、*何を* 測定しているかを明示（クロスファンクショナル対応）。

---

## 🆕 実装能力マトリックス（v2.0）

第8の競合チャート — **30項目 × グローバルトップ競合 5〜10社**:

```
                       Target  Signal  WhatsApp  Telegram  iMessage  Wire
暗号化（核心差別化）
  E2E (Signal Protocol) ○      ○       ○        △         ○         ○
  PQXDH / ML-KEM-1024   ○      ○       ×        ×         ○         ?
  Double Ratchet        ○      ○       ○        ×         ○         ○
  libsignal / BoringSSL ○      ○       ×        ×         ○         △
  自前 crypto 実装なし   ○      ○       △        ×         ○         △
  Forward Secrecy + PCS ○      ○       ○        △         ○         ○
  Zero-Knowledge Proof  △      ×       ×        ×         ×         ×
  暗号研究・論文公開     ○      ×       ×        ×         △         ×
  ...
```

4状態マーキング（日本式テックレーティング標準）:
- **○ verified**（公開資料で実装確認済み）
- **△ claimed**（主張あり、検証未完）
- **× not_implemented**（明示的に未対応）
- **? unknown**（判定不能 — 推測より優先）

---

## 📄 22ページ PDF の中身

**v1.x コア（15ページ — 完全保持）**

| # | セクション | 内容 |
|---|-----------|------|
| 1 | 表紙 | 黒 + Arc sky (#5271FF) アクセント、プロジェクト名・スコア・グレード |
| 2 | スコアダッシュボード | 6次元横棒グラフ + バロメーター |
| 3 | エグゼクティブサマリー | ビジネス + 技術サマリー |
| 4 | SWOT 分析 | 2×2 ビジュアルグリッド + エビデンス + ビジネスアナロジー |
| 5 | スコア内訳 | 軸別の根拠・可能性 |
| 6 | テクレベル評価 | Lv.1〜10 ゲージ + 平易な解説 |
| 7 | 将来性評価 | 1/3/5 年予測（信頼度付き） |
| 8 | 戦略アドバイス | 即座 / 中期 / 長期 |
| 9 | 投資判断 | 推奨 / リスク / アップサイド / 類似企業 |
| 10 | レッドフラグ | 深刻度別（Critical/High/Medium/Low） |
| 11 | サイト検証 | 10項目の信頼性監査（URL 提供時のみ） |
| 12-14 | 競合分析 | 7チャート × 6市場、軸説明キャプション付き |
| 15 | 用語集 | 全技術用語に非エンジニア向け注釈 |

**v2.0 追加（4 新ページ）**

| # | セクション | 内容 |
|---|-----------|------|
| 16 | **Atlas 4軸ダッシュボード** | 高速化/安定化/軽量化/超高度セキュリティ 横棒グラフ |
| 17 | **超高度セキュリティ サブ内訳** | 5 サブ項目、暗号化（30%）が視覚的に最長バー |
| 18 | **実装能力マトリックス** | 30項目 × トップ競合、○△×? マーキング |

---

## 🛠️ 使い方

```bash
# カレントディレクトリ、日本語 PDF
dde prompt --pdf --lang ja

# GitHub リポをステージ指定で
dde prompt owner/repo --pdf --lang ja --stage seed

# 非対話モード（プロンプト入力できない AI ターミナル向け）
dde prompt --pdf --lang ja \
  --url https://example.com \
  --url https://docs.example.com

# 直接 BYOK マルチAIクロス検証（オプション）
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_AI_API_KEY=AIza...
export OPENAI_API_KEY=sk-...
dde analyze owner/repo
```

---

## 🔐 セキュリティ & OSS 哲学

| 保証 | 実装 |
|------|------|
| **ローカル完結処理** | `dde prompt` は外部送信ゼロ |
| **レポートにソースコードなし** | PDF は所見のみ |
| **API 0-day 保持** | `dde analyze` は無保持エンドポイント使用 |
| **自動セキュリティ CI** | CodeQL · Dependabot · pip-audit · safety · osv-scanner · gitleaks |
| **ブランチ保護** | `main` は PR + CI + シークレットプッシュ保護必須 |
| **Private リポ PAT** | メモリ上で 1 回使用後即破棄 |

脆弱性報告: [SECURITY.md](SECURITY.md) — 48 時間以内の初回応答 SLA。

### なぜ OSS はリスクではなくセキュリティ機能なのか

オープンソースは全コード監査可能。隠しバックドアなし。ブラックボックススコアリングなし。
これは Signal および libsignal と同じ哲学: **透明性こそ信頼の源泉**。

---

## 📜 ライセンス

[Apache License 2.0](LICENSE) — Copyright © 2026 Takayuki Miyano / Atlas Associates

---

<div align="center">

**Powered by Due Diligence Engine — Takayuki Miyano / Atlas Associates**

`v0.2.0` — 黒 + `#5271FF` ブランドアイデンティティ · テック美の徹底

</div>
