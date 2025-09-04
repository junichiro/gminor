# gminor

GitHub生産性メトリクス可視化ツール

## プロジェクト構造

```
gminor/
├── src/                          # ソースコード
│   ├── data_layer/              # データ層 - データベース、API、ファイル操作
│   ├── business_layer/          # ビジネス層 - ビジネスロジック、計算処理
│   ├── presentation_layer/      # プレゼンテーション層 - UI、CLI、レポート
│   └── __init__.py
├── tests/                       # テストコード
├── logs/                        # ログファイル（gitignore済み）
├── data/                        # データファイル（gitignore済み）
├── output/                      # 出力ファイル（gitignore済み）
├── requirements.txt             # 依存関係
├── .env.example                # 環境変数設定例
└── .gitignore                  # Git除外設定
```

## セットアップ

1. リポジトリをクローン
2. 依存関係をインストール:
   ```bash
   pip install -r requirements.txt
   ```
3. 環境変数を設定:
   ```bash
   cp .env.example .env
   # .envファイルを編集して適切な値を設定
   ```

## 開発方針

- **テスト駆動開発（TDD）**: t-wadaスタイルのRED-GREEN-REFACTORサイクル
- **レイヤードアーキテクチャ**: データ層、ビジネス層、プレゼンテーション層の分離
- **品質重視**: 全ての警告を解決し、クリーンなビルドを維持