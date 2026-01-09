# Inflow Funnel Template (ROXX / BigQuery)

## Goal
- 何を意思決定するための指標か（例：流入別の通電率/面談率/売上率の比較）
- 出力は「集計」か「明細（1人粒度）」か

## Grain (固定)
- 1 row = 1人 × 登録月 × 初回流入
- 初回流入は生涯固定（再帰属なし）
- コホートは登録月（Asia/Tokyo）

## Period
- 対象登録月: [YYYY-MM] 〜 [YYYY-MM]
- 参照するイベント/売上の計測窓: [例: 登録後30日/90日/180日]

## Inflow definition (固定)
- 初回流入 = 登録日時（JST）から遡って最大30日内の最初のセッションの流入
- 優先度: campaign > utm_source/medium > referrer > direct
- 計測不能は unknown

## Funnel stages (要プロジェクト入力)
- F0: 登録（users.registration_ts）
- F1: [例: 初回架電]（定義/テーブル/条件）
- F2: [例: 初回通電]（定義/テーブル/条件）
- F3: [?atetime
  - 各ステージ bool, 各ステージ達成日時
  - flags（internal/bot/test/reactivated）
- 付随: 2本の検証SQL（一意性、unknown比率）

## Notes
- タイムゾーンは Asia/Tokyo で判定（DATE/DATETIMEはJST）
- パーティション前提（eventsは日付で絞る）
