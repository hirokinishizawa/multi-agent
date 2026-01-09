# Multi-Agent Playbook (ROXX / Data)

## 0. Goal
- PO（あなた）が意思決定できるアウトプットを、ローカル multi-agent が自立的に生成できる状態にする
- 最終的にこのチャット（SM/Coach）が不要になること

## 1. Roles
### PO (You)
- 目的・優先度・Done（DoD）を決める
- ビジネス定義の最終決裁（例：登録数=SFDC Lead作成数 など）

### Dev Team (Local multi-agent)
- ドラフト生成〜完成版出力までを担う（最終的に）
- runs/ に再現可能な成果物（要求＋SQL＋検証＋メモ）を保存する

### SM/Coach (This chat)
- 立ち上げ期はFinisher/Reviewerを兼務しつつ、修正点をルール化してローカルへ移植する
- ボトルネック除去（環境/速度/命名/品質）

## 2. Output Contract (must)
### 2.1 SQL Must Rules
- Timezone: Asia/Tokyo を基準に日付境界を切る
- Period filter: 半開区間で統一する（>= start AND < end）
le = roxx-z-career-roxx-jinzai-data.dwh.dwh_talent_lead
- Key = id (unique)
- registration_date = DATE (JST)
- inflow = first_registration_source (first-touch fixed)
- Grain = registration_month x first_registration_source
- Metric = lead_registrations = COUNT(*)
- Period = last 12 months (including current month to date)

### 3.2 Notes
- zcp_talent_id は転職支援が可能な求職者に付与される後段指標（今回は分母にしない）

## 4. Sprint Routine (lightweight)
- Planning: POがタスク定義（1-3行）を提示
- Run: local multi-agentで生成 → runs/に保存
- Review: must rulesに照らして不足があれば修正
- Retrospective: 修正点はこのPLAYBOOKに追記し、次回から自動化の材料にする
