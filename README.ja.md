<div align="center">

# Due Diligence Engine

**3社のAIがクロス検証。信頼できるひとつの判定を。**

1社のAIだけでは盲点がある。DDEはClaude、Gemini、ChatGPTを**同時並列実行** — 各社が独立評価し、クロス検証でバイアスのない投資スコアを生成。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![AI](https://img.shields.io/badge/AI-Claude_%7C_Gemini_%7C_ChatGPT-orange.svg)](https://github.com/taka-avantgarde/due-diligence-engine)

[English](README.md) | [日本語](README.ja.md)

</div>

---

## マルチAIクロス検証

```
         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │   Claude     │  │   Gemini    │  │  ChatGPT    │
         │  (Anthropic) │  │  (Google)   │  │  (OpenAI)   │
         └──────┬───────┘  └──────┬──────┘  └──────┬──────┘
                │                 │                 │
                └────────┬────────┴────────┬────────┘
                   ┌─────▼─────────────────▼─────┐
                   │   クロス検証エンジン          │
                   │   + サイト信頼性チェック       │
                   └──────────────┬───────────────┘
                         ┌────────▼────────┐
                         │  統合スコア       │
                         │  + 信頼性指標     │
                         └─────────────────┘
```

---

## まず試してみる

**https://due-diligence-engine.web.app/dashboard/**

公開GitHubリポジトリのURLを貼って「分析」をクリック。

> 基本分析（ローカルコードスキャン）は無料。AI分析には自分のAPIキー — **BYOK（Bring Your Own Key）** をご利用ください。

---

## 料金プラン

| プラン | 費用 | AIプロバイダー | 機能 |
|--------|------|---------------|------|
| **無料（ローカルのみ）** | 無料 | なし | コード構造、Git履歴、依存関係スキャン |
| **BYOK** | 無料（API費用は自己負担） | Claude / Gemini / ChatGPT（1〜3社） | フルAI分析 + クロス検証 |
| **Pro分析（日本のみ）** | **¥3,000 / 社** | Claude + Gemini（当社管理） | AI自動レポート + オンライン会議サポート |

> **BYOK:** APIキー1つから始められます。プロバイダーを追加するとクロス検証が自動有効化。

> **Pro分析:** 1社¥3,000で自動レポート生成 + オンライン会議でリアルタイムサポート。お気軽にお問い合わせください。
>
> **[Atlas Associates](https://www.atlasassociates.io/)** — support@atlasassociates.io

---

## 機能一覧

| 機能 | 説明 |
|------|------|
| **マルチAIクロス検証** | Claude + Gemini + ChatGPTが独立評価→クロス検証 |
| **BYOK（Bring Your Own Key）** | 自分のAPIキーで分析。Claude・Gemini・ChatGPT対応。1社でも3社でも。ベンダーロックインなし |
| **GitHub Privateリポ対応** | PATベースの一時アクセス |
| **AIウォッシュ検出** | 「独自AI」と偽るAPIラッパーを検出 |
| **Git履歴フォレンジック** | コミット履歴の不審パターン（DD直前の急造など）を分析 |
| **10段階技術レベル評価** | 各軸Lv.1〜10で明確な基準付き |
| **PDF出力** | 投資委員会向けプロフェッショナルPDF |
| **切断 & 破棄** | ワンクリックでデータ消去 + 破棄証明書 |
| **バイリンガルUI** | English / 日本語 切替 |

---

## スコアリング

### 最終スコアの算出式

```
最終スコア = ヒューリスティック分析 (30%) + AI平均スコア (70%)
```

### スコアバロメーター

```
  0          40          60          75          90        100
  |----------|-----------|-----------|-----------|----------|
  F          D           C           B           A
  投資不可   高リスク    懸念あり    条件付き    有力候補
                                     投資可能
```

| スコア | 評価 | 推奨アクション |
|--------|------|----------------|
| 90–100 | 🏆 **A** | 有力な投資候補 |
| 75–89  | ✅ **B** | 条件付きで投資可能 |
| 60–74  | ⚡ **C** | 重要な懸念あり — 精査が必要 |
| 40–59  | ⚠️ **D** | 高リスク |
| 0–39   | 🚫 **F** | 投資不可 |

---

### 6軸評価

| 評価軸 | 重み | 検出内容 |
|--------|------|----------|
| 技術独自性 | 25% | APIラッパー vs 本物のIP |
| 技術先進性 | 20% | 技術スタックの先進度 |
| 実装深度 | 20% | PoC vs 本番品質 |
| アーキテクチャ品質 | 15% | 設計品質 |
| 主張整合性 | 10% | ピッチ vs 現実 |
| セキュリティ態勢 | 10% | セキュリティ成熟度 |

---

### 10段階技術レベル評価

各軸は **Lv.1〜10** の明確な基準でレーティング：

```
Lv.1 ──── Lv.2 ──── Lv.3 ──── Lv.4 ──── Lv.5 ──── Lv.6 ──── Lv.7 ──── Lv.8 ──── Lv.9 ──── Lv.10
 ▓          ▓▓         ▓▓▓        ▓▓▓▓       ▓▓▓▓▓      ▓▓▓▓▓▓     ▓▓▓▓▓▓▓    ▓▓▓▓▓▓▓▓   ▓▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓▓▓
最低水準                                      業界標準                                                最高水準
```

| レベル | 技術独自性 | 実装深度 | アーキテクチャ品質 |
|--------|-----------|---------|-----------------|
| Lv.1  | コピー・独自コードなし | UIモックのみ | スパゲッティコード |
| Lv.3  | 複数API組み合わせ | 動くプロトタイプ | 基本的なレイヤー分離 |
| Lv.5  | 既存技術の大幅拡張＋独自アルゴリズム一部 | Beta・基本テストあり | 関心の分離が明確 |
| Lv.7  | コア技術が独自実装 | 本番運用・監視完備 | マイクロサービス |
| Lv.10 | 世界最先端・既存技術を置き換える可能性 | ミッションクリティカル | 分散システム |

---

## クイックスタート

```bash
git clone https://github.com/taka-avantgarde/due-diligence-engine.git
cd due-diligence-engine
pip install -e .
```

### 設定

```bash
# AIプロバイダー（1社、2社、または3社全て設定可能）
export ANTHROPIC_API_KEY="sk-ant-..."     # Claude
export GOOGLE_AI_API_KEY="AIza..."        # Gemini
export OPENAI_API_KEY="sk-..."            # ChatGPT
```

### CLI

```bash
# GitHub URLで分析
dde analyze https://github.com/some-startup/their-product

# ローカルのみ（無料、AIなし）
dde analyze some-startup/repo --skip-ai
```

---

## Privateリポジトリアクセス（PAT）

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → **`repo`** スコープにチェック → 有効期限7日
3. トークン（`ghp_...`）をダッシュボードに貼り付け

**セキュリティ:** PATはメモリ上で `git clone` に1回使用後、即座に破棄。保存されません。

---


## データセキュリティ

| 保証事項 | 実装方法 |
|---------|---------|
| クラウド保存なし | 暗号化tmpfsで処理 |
| レポートにコードなし | PDFには所見のみ |
| 暗号消去 | 3パスランダム上書き + 破棄証明書 |
| API 0-day保持 | Anthropic / Google / OpenAI — データ保持なし |

---

## 免責事項

本ツールは**投資判断を支援するための技術分析**を提供します。投資助言ではありません。投資判断には必ず専門家にご相談ください。

---

## ライセンス

[Apache License 2.0](LICENSE)

---

<div align="center">

**Powered by Claude (Anthropic) + Gemini (Google) + ChatGPT (OpenAI)**

</div>
