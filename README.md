# gminor - GitHub Repository Productivity Metrics Visualization Tool

GitHub生産性メトリクス可視化ツール

複数のGitHubリポジトリにおける開発生産性を可視化するツールです。生産性を「週次のマージされたPR数 ÷ その週にPRを作成したユニークなエンジニア数」として定義し、週次推移と4週移動平均をインタラクティブなグラフで表示します。

## 主な機能

- **複数リポジトリ対応**: 複数のGitHubリポジトリを横断した生産性分析
- **自動データ取得**: GitHub APIを使用したマージ済みPRの自動収集
- **インクリメンタル更新**: 差分のみを取得する効率的なデータ同期
- **タイムゾーン対応**: UTCでデータ収集、JST（設定可能）で表示
- **インタラクティブ可視化**: Plotlyによるズーム・フィルター機能付きHTML出力
- **移動平均分析**: 4週移動平均による長期トレンド分析

## 生産性の定義

```
週次生産性 = その週にマージされたPR数 ÷ その週にPRを作成したユニークなエンジニア数
```

- 週の開始: 月曜日（設定可能）
- 複数リポジトリ選択時: 同一作者は1人としてカウント
- タイムゾーン: データ収集はUTC、集計・表示は設定されたタイムゾーン（デフォルト: JST）

## 必要要件

- Python 3.10以上
- GitHub Personal Access Token（Classic）
- SQLite（自動作成）

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/gminor.git
cd gminor
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの準備

```bash
# 設定ファイルのコピー
cp config.yaml.example config.yaml

# 環境変数ファイルの作成
cp .env.example .env
```

### 4. GitHub Personal Access Tokenの設定

`.env`ファイルを編集してGitHub tokenを設定：

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**必要な権限**: `repo` スコープ（プライベートリポジトリの場合）、`public_repo`（パブリックリポジトリの場合）

## 設定

### config.yaml の主要設定

```yaml
# GitHub設定
github:
  repositories:
    - "organization/repo1"
    - "organization/repo2"
    - "organization/repo3"
  
  fetch:
    initial_days: 180      # 初回取得期間（日）
    batch_size: 100        # API一度の取得数
    rate_limit_buffer: 100 # レート制限バッファ

# タイムゾーン設定
timezone:
  display: "Asia/Tokyo"    # 集計・表示用タイムゾーン

# 集計設定
aggregation:
  week_start_day: "monday" # 週の開始曜日

# 出力設定
output:
  html_path: "./output/productivity_report.html"
  chart_type: "combined"   # "combined", "separate", "both"

# データベース設定
database:
  path: "./data/productivity.db"
```

## 使用方法

### 初回データ取得

```bash
# デフォルト180日分を取得
python main.py init

# 期間を指定して取得
python main.py init --days 365
```

### 差分更新

```bash
# 最終更新以降のデータを取得
python main.py update
```

### 可視化

```bash
# データ取得せずに可視化のみ実行
python main.py visualize

# タイムゾーンを指定して可視化
python main.py visualize --timezone "America/New_York"
```

### その他のコマンド

```bash
# 特定期間のデータを再取得
python main.py fetch --from 2024-01-01 --to 2024-12-31

# 統計情報表示
python main.py stats

# 設定確認
python main.py config

# データベースクリーンアップ
python main.py cleanup --before 2024-01-01
```

## プロジェクト構造

```
gminor/
├── src/                          # ソースコード
│   ├── data_layer/              # データ層 - GitHub API、データベース操作
│   │   ├── github_client.py     # GitHub APIクライアント
│   │   ├── models.py            # SQLAlchemyモデル定義
│   │   └── database.py          # DB接続・セッション管理
│   │
│   ├── business_layer/          # ビジネス層 - メトリクス計算、データ同期
│   │   ├── aggregator.py        # メトリクス計算ロジック
│   │   ├── sync_manager.py      # データ同期・差分取得
│   │   ├── timezone_handler.py  # タイムゾーン変換処理
│   │   └── config_loader.py     # 設定ファイル読み込み
│   │
│   └── presentation_layer/      # プレゼンテーション層 - CLI、可視化
│       ├── visualizer.py        # グラフ生成
│       └── cli.py              # CLIコマンド定義
│
├── tests/                       # テストコード
├── logs/                        # ログファイル（gitignore済み）
├── data/                        # データファイル（gitignore済み）
├── output/                      # 出力ファイル（gitignore済み）
├── config.yaml                  # 設定ファイル
├── requirements.txt             # 依存関係
├── .env.example                # 環境変数設定例
└── main.py                     # エントリーポイント
```

## データベース設計

### Pull Requests テーブル
- GitHub PRの基本情報を格納
- UTCでタイムスタンプを保存
- repo_name + pr_numberで一意性保証

### Weekly Metrics テーブル
- 週次集計データをキャッシュ
- 設定されたタイムゾーンで集計
- パフォーマンス向上のための事前計算

### Sync Status テーブル
- 各リポジトリの同期状態を管理
- 差分更新の効率化

## 技術仕様

### 使用技術
- **言語**: Python 3.10+
- **GitHub API**: PyGithub
- **データベース**: SQLite3 + SQLAlchemy
- **データ処理**: pandas
- **可視化**: Plotly
- **CLI**: Click
- **設定管理**: PyYAML
- **タイムゾーン処理**: pytz

### パフォーマンス最適化
- GitHub API レート制限対応（5,000リクエスト/時）
- 差分更新による効率的なデータ取得
- 週次メトリクスのキャッシュ機能
- バッチ処理による大量データ処理

## 出力例

生成されるHTMLレポートには以下が含まれます：

- **統計サマリー**: 平均生産性、最高・最低生産性、総PR数など
- **インタラクティブグラフ**: 
  - 週次生産性の推移（青線、マーカー付き）
  - 4週移動平均（赤色破線）
  - ズーム・パン機能
  - ホバー情報（日付、PR数、貢献者数）
- **メタデータ**: 生成日時、対象期間、対象リポジトリ

## 開発方針

- **テスト駆動開発（TDD）**: RED-GREEN-REFACTORサイクル
- **レイヤードアーキテクチャ**: 関心事の分離による保守性向上
- **品質重視**: 全警告解決、型ヒント、docstring完備
- **セキュリティ**: トークン管理、SQLインジェクション対策

## トラブルシューティング

### GitHub API レート制限エラー
```
Rate limit exceeded. Waiting for reset...
```
- 自動的に待機します
- `rate_limit_buffer`設定で余裕を調整可能

### データベース接続エラー
```
sqlite3.OperationalError: database is locked
```
- 他のプロセスがDBを使用中
- プロセス終了後に再実行

### 設定ファイルエラー
```
ConfigError: 設定ファイルが見つかりません
```
- `config.yaml`が存在するか確認
- `config.yaml.example`からコピー

## ライセンス

MIT License

## コントリビューション

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Run tests (`pytest`)
4. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

## 関連リンク

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [Plotly Python Documentation](https://plotly.com/python/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)