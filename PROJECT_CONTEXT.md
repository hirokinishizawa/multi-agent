# PROJECT_CONTEXT (SoT)

このリポジトリにおけるマルチエージェント運用の「前提」「ルール」「変更方針」をここに集約する。
チャットは揮発するため、前提の正はこのファイル。

## Scope
- マルチエージェント（Framer / SQLBuilder / Finisher）で、ユーザー依頼を BigQuery SQL に落とす。
- 成果物は `runs/` に保存し、再現可能にする。

## Source of Truth
- 前提・方針: `PROJECT_CONTEXT.md`
- 実行履歴（自動追記）: `STATE.md`
- 実装の正: `src/agents.py`, `src/run.py`
- 成果物: `runs/*.md`, `runs/*_manifest.json`, `runs/*_production.sql`, `runs/*_validation_*.sql`

## Output Contract (Finisher)
- Asia/Tokyo を期間境界にする
- half-open interval: `>= start AND < end`
- Grain を明記
- NULL/空の扱いを明記
- Production SQL 1本 + Validation SQL 2本（合計3本）を必ずコードブロックで出す
- ユーザーがフルテーブル名を指定したら placeholder を出さない
- CLI向けメモでは zsh のバッククォート（`）は使わない注意を入れる（command substitution 回避）

## Change Policy (重要: ここがあなたの要件)
### 1) 変更が入る場所
- エージェントの振る舞い変更: `src/agents.py` の system 変更
- 出力形式/保存/manifest/抽出の変更: `src/run.py` の変更

### 2) 変更手順（必須）
- 変更の意図をこの `PROJECT_CONTEXT.md` の該当セクションに追記する
- `python -m src.run "<テスト依頼>"` を1回通す
- `runs/` に md + manifest + sql(3本) が出ることを確認
- `STATE.md` が自動更新されていることを確認

### 3) 後方互換ルール
- `runs/` の既存成果物は壊さない（フォーマット互換を維持）
- どうしても破壊的変更なら、manifest に version を追加し、STATEに明記する

## Auto-updated (by run.py)
下のブロックは `run.py` が最新run情報を自動更新する（手編集しない）。

<!-- AUTO:LAST_RUN_START -->
- 2026-01-09 12:32:15 JST
- request: テスト：git hash 取得確認
- markdown: `20260109_123215_テストgit_hash_取得確認.md`
- manifest: `20260109_123215_テストgit_hash_取得確認_manifest.json`
- sql: `20260109_123215_テストgit_hash_取得確認_production.sql`, `20260109_123215_テストgit_hash_取得確認_validation_1.sql`, `20260109_123215_テストgit_hash_取得確認_validation_2.sql`
<!-- AUTO:LAST_RUN_END -->
