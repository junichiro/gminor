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

### 1. 前提条件
- Python 3.8以上
- Git

### 2. インストール
1. リポジトリをクローン
   ```bash
   git clone https://github.com/junichiro/gminor.git
   cd gminor
   ```

2. 仮想環境を作成・アクティベート
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. 依存関係をインストール
   ```bash
   pip install -r requirements.txt
   ```

### 3. 設定

1. GitHub Personal Access Token の取得
   - GitHub Settings → Developer settings → Personal access tokens
   - 必要な権限: `repo` (private repositories), `public_repo` (public repositories)

2. 環境変数を設定
   ```bash
   export GITHUB_TOKEN="your_github_personal_access_token"
   ```

3. 設定ファイルを編集
   ```bash
   # config.yamlを編集して分析対象リポジトリを設定
   vim config.yaml
   ```

### 4. 使用方法

#### 初回データ取得
```bash
# デフォルト（過去180日間）のデータを取得
python main.py init

# 過去90日間のデータを取得
python main.py init --days 90
```

#### グラフ生成
```bash
# 生産性グラフを生成（output/productivity_chart.html）
python main.py visualize
```

#### ヘルプ
```bash
python main.py --help
python main.py init --help
python main.py visualize --help
```

## 開発方針

- **テスト駆動開発（TDD）**: t-wadaスタイルのRED-GREEN-REFACTORサイクル
- **レイヤードアーキテクチャ**: データ層、ビジネス層、プレゼンテーション層の分離
- **品質重視**: 全ての警告を解決し、クリーンなビルドを維持