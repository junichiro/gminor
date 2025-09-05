# GitHub リポジトリ生産性メトリクス可視化ツール - 実装指示書

## プロジェクト概要
複数の GitHub リポジトリにおける開発生産性を可視化するツールを作成してください。生産性は「週次のマージされた PR 数 ÷ その週に PR を作成したユニークなエンジニア数」と定義し、週次推移と4週移動平均をグラフ化します。データは UTC で収集し、集計・表示時にはタイムゾーン（デフォルト: JST）に変換します。

## 機能要件

### 必須機能
1. **データ取得**
   - 複数の GitHub リポジトリから merged PR を取得
   - Classic Personal Access Token による認証
   - 初回実行時：指定期間（デフォルト180日）の過去データを取得
   - 2回目以降：最終取得日から現在までの差分のみ取得
   - 取得時のタイムスタンプは UTC で保存

2. **データ集計**
   - 設定されたタイムゾーン（デフォルト: Asia/Tokyo）で週次集計
   - 週の開始は月曜日
   - PR 作成者（author）のユニーク数をカウント
   - 生産性 = merged PR 数 ÷ PR 作成者数 を計算
   - 4週移動平均を算出

3. **データ可視化**
   - 週次生産性の推移グラフ
   - 4週移動平均の重ね描き
   - Plotly でインタラクティブな HTML ファイルとして出力
   - グラフの日付表示は設定されたタイムゾーンを使用

4. **データ永続化**
   - SQLite データベースにデータを保存
   - 差分更新をサポート
   - UTC でタイムスタンプを保存

## 技術仕様

### 使用技術
- 言語: Python 3.10+
- GitHub API: PyGithub
- データベース: SQLite3 + SQLAlchemy
- データ処理: pandas
- 可視化: Plotly
- CLI: Click
- 設定管理: PyYAML
- タイムゾーン処理: pytz

### ディレクトリ構造
```
github-productivity-tracker/
├── src/
│   ├── data_layer/
│   │   ├── __init__.py
│   │   ├── github_client.py      # GitHub API クライアント
│   │   ├── models.py             # SQLAlchemy モデル定義
│   │   └── database.py           # DB 接続・セッション管理
│   │
│   ├── business_layer/
│   │   ├── __init__.py
│   │   ├── aggregator.py         # メトリクス計算ロジック
│   │   ├── sync_manager.py       # データ同期・差分取得
│   │   └── timezone_handler.py   # タイムゾーン変換処理
│   │
│   └── presentation_layer/
│       ├── __init__.py
│       ├── visualizer.py         # グラフ生成
│       └── cli.py               # CLI コマンド定義
│
├── config.yaml                   # 設定ファイル
├── main.py                       # エントリーポイント
├── requirements.txt
├── .env.example                  # 環境変数サンプル
├── .gitignore
├── README.md
└── tests/                        # テストディレクトリ
    ├── __init__.py
    ├── test_aggregator.py
    ├── test_github_client.py
    └── test_sync_manager.py
```

## データモデル

### SQLite テーブル構造

```sql
-- Pull Requests テーブル（タイムスタンプは全て UTC）
CREATE TABLE pull_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_name TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    author TEXT NOT NULL,
    merged_at DATETIME NOT NULL,  -- UTC
    title TEXT,
    created_at DATETIME,           -- UTC
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- UTC
    UNIQUE(repo_name, pr_number)
);

-- 週次集計テーブル（キャッシュ）
CREATE TABLE weekly_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start DATE NOT NULL,      -- 集計タイムゾーンでの週開始日
    week_end DATE NOT NULL,        -- 集計タイムゾーンでの週終了日
    repo_name TEXT,                -- NULL の場合は全リポジトリ合計
    pr_count INTEGER NOT NULL,
    unique_authors INTEGER NOT NULL,
    productivity REAL NOT NULL,
    moving_avg_4w REAL,
    timezone TEXT NOT NULL,        -- 集計時のタイムゾーン
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- UTC
    UNIQUE(week_start, repo_name, timezone)
);

-- 同期状態管理テーブル
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_name TEXT NOT NULL UNIQUE,
    last_synced_at DATETIME,      -- UTC
    last_pr_merged_at DATETIME,   -- UTC
    total_prs_synced INTEGER DEFAULT 0
);

-- インデックス
CREATE INDEX idx_pr_merged_at ON pull_requests(merged_at);
CREATE INDEX idx_pr_repo_merged ON pull_requests(repo_name, merged_at);
CREATE INDEX idx_weekly_metrics_week ON weekly_metrics(week_start, timezone);
```

## 設定ファイル仕様

### config.yaml
```yaml
# GitHub 設定
github:
  # リポジトリリスト（owner/repo 形式）
  repositories:
    - "organization/repo1"
    - "organization/repo2"
    - "organization/repo3"
  
  # データ取得設定
  fetch:
    initial_days: 180      # 初回取得期間（日）
    batch_size: 100        # API 一度の取得数
    rate_limit_buffer: 100 # レート制限バッファ（残り何回で待機）

# タイムゾーン設定
timezone:
  # 集計・表示用タイムゾーン（IANA タイムゾーン識別子）
  display: "Asia/Tokyo"    # デフォルト: Asia/Tokyo
  # データベース保存は常に UTC

# 集計設定
aggregation:
  week_start_day: "monday"  # 週の開始曜日
  
# 出力設定
output:
  html_path: "./output/productivity_report.html"
  # 複数リポジトリの表示方法
  chart_type: "combined"    # "combined": 統合グラフ, "separate": 個別グラフ, "both": 両方
  
# データベース設定
database:
  path: "./data/productivity.db"

# ロギング設定
logging:
  level: "INFO"            # DEBUG, INFO, WARNING, ERROR
  file: "./logs/app.log"
```

### .env
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

## CLI インターフェース

```bash
# 初回実行（過去180日分を取得）
python main.py init

# 初回実行（期間指定）
python main.py init --days 365

# 差分更新
python main.py update

# 可視化のみ実行（データ取得せず）
python main.py visualize

# タイムゾーンを指定して可視化
python main.py visualize --timezone "America/New_York"

# 特定期間のデータを再取得
python main.py fetch --from 2024-01-01 --to 2024-12-31

# 統計情報表示
python main.py stats

# データベースのクリーンアップ（古いキャッシュ削除）
python main.py cleanup --before 2024-01-01

# 設定確認
python main.py config
```

## 実装詳細仕様

### タイムゾーン処理
```python
# timezone_handler.py の主要メソッド
class TimezoneHandler:
    def __init__(self, display_timezone: str = "Asia/Tokyo"):
        """表示用タイムゾーンを設定"""
        
    def utc_to_local(self, dt: datetime) -> datetime:
        """UTC から設定されたタイムゾーンに変換"""
        
    def local_to_utc(self, dt: datetime) -> datetime:
        """設定されたタイムゾーンから UTC に変換"""
        
    def get_week_boundaries(self, date: datetime) -> tuple[datetime, datetime]:
        """指定日付を含む週の開始・終了日時を返す（ローカルタイムゾーン）"""
```

### GitHub API クライアント
```python
# github_client.py の主要メソッド
class GitHubClient:
    def __init__(self, token: str):
        """認証トークンで初期化"""
        
    def fetch_merged_prs(self, repo: str, since: datetime, until: datetime = None) -> list[dict]:
        """指定期間のマージ済み PR を取得（UTC）"""
        
    def get_rate_limit_status(self) -> dict:
        """API レート制限の状態を取得"""
        
    def wait_for_rate_limit_reset(self):
        """レート制限リセットまで待機"""
```

### 集計ロジック
```python
# aggregator.py の主要メソッド
class ProductivityAggregator:
    def __init__(self, timezone_handler: TimezoneHandler):
        """タイムゾーンハンドラーで初期化"""
        
    def calculate_weekly_metrics(self, prs: list[dict]) -> pd.DataFrame:
        """週次メトリクスを計算"""
        
    def calculate_moving_average(self, df: pd.DataFrame, window: int = 4) -> pd.Series:
        """移動平均を計算"""
        
    def aggregate_by_repo(self, prs: list[dict]) -> dict:
        """リポジトリ別に集計"""
```

## 実装の優先順位

### フェーズ1（MVP - 必須実装）
1. **基盤構築**
   - プロジェクト構造の作成
   - 依存関係のセットアップ（requirements.txt）
   - 設定ファイルの読み込み機能

2. **データ層**
   - SQLAlchemy モデル定義
   - データベース初期化
   - GitHub API クライアント（基本的な PR 取得）

3. **ビジネス層**
   - タイムゾーンハンドラー
   - 週次集計ロジック（PR 数、ユニーク作成者数、生産性）
   - 初回データ取得機能

4. **プレゼンテーション層**
   - 基本的なグラフ生成（週次推移のみ）
   - CLI の init と visualize コマンド

### フェーズ2（機能拡張）
1. **差分同期機能**
   - sync_status テーブルの活用
   - 最終取得日以降のデータのみ取得
   - update コマンドの実装

2. **高度な集計と可視化**
   - 4週移動平均の計算と表示
   - 動的リポジトリフィルター機能
   - 統合ビューと個別ビューの切り替え
   - 統計情報の動的更新

3. **エラーハンドリング**
   - API レート制限対応
   - ネットワークエラーのリトライ
   - 進捗表示（tqdm）

### フェーズ3（品質向上）
1. **テスト**
   - pytest によるユニットテスト
   - モックを使った API テスト

2. **運用機能**
   - ログ機能
   - stats, cleanup コマンド
   - パフォーマンス最適化

## 品質要件

### コード品質基準
- **PEP 8 準拠**：flake8 でチェック
- **型ヒント**：全ての関数に typing を使用
- **Docstring**：Google スタイルで記述
- **例外処理**：適切な try-except と カスタム例外クラス
- **DRY 原則**：重複コードを避ける
- **SOLID 原則**：単一責任、依存性注入を意識

### エラーハンドリング要件
```python
# カスタム例外クラスの例
class GitHubAPIError(Exception):
    """GitHub API 関連のエラー"""

class RateLimitError(GitHubAPIError):
    """レート制限エラー"""

class DataSyncError(Exception):
    """データ同期エラー"""
```

### ロギング要件
- DEBUG: API リクエスト詳細、SQL クエリ
- INFO: 処理開始/終了、取得件数
- WARNING: リトライ、スキップされたデータ
- ERROR: 例外、処理失敗

## 出力仕様

### HTML レポート構成
```html
<!-- 生成される HTML の構造 -->
<!DOCTYPE html>
<html>
<head>
    <title>GitHub Repository Productivity Report</title>
    <!-- Plotly.js -->
</head>
<body>
    <h1>生産性レポート</h1>
    <div class="metadata">
        <p>生成日時: 2024-XX-XX HH:MM JST</p>
        <p>対象期間: 2024-XX-XX 〜 2024-XX-XX</p>
        <p>対象リポジトリ: repo1, repo2, repo3</p>
    </div>
    
    <div class="statistics">
        <h2>統計サマリー</h2>
        <ul>
            <li>平均生産性: X.XX</li>
            <li>最高生産性: X.XX（YYYY-MM-DD の週）</li>
            <li>最低生産性: X.XX（YYYY-MM-DD の週）</li>
            <li>総 PR 数: XXX</li>
            <li>総貢献者数: XX</li>
        </ul>
    </div>
    
    <div id="productivity-chart">
        <!-- Plotly グラフ -->
    </div>
</body>
</html>
```

### グラフ仕様
- X軸: 週の開始日（YYYY-MM-DD 形式、設定されたタイムゾーン）
- Y軸: 生産性（PR数/人）
- 系列1: 週次生産性（青色、マーカー付き線）
- 系列2: 4週移動平均（赤色、破線）
- ホバー情報: 日付、PR数、貢献者数、生産性値
- インタラクティブ機能: ズーム、パン、系列の表示/非表示

## 注意事項・制約事項

1. **GitHub API レート制限**
   - 認証済み: 5,000 リクエスト/時
   - レート制限に近づいたら自動待機
   - 残り100リクエストでバッファ

2. **パフォーマンス考慮**
   - 大量 PR の場合はバッチ処理
   - 週次メトリクスはキャッシュ（weekly_metrics テーブル）
   - JavaScript での再計算は効率的なアルゴリズムを使用

3. **データ整合性**
   - トランザクション管理
   - ユニーク制約でデータ重複防止
   - タイムゾーン変換の一貫性確保
   - **作者の重複排除**: メールアドレスまたはユーザー名で識別

4. **合算値計算の仕様**
   - 複数リポジトリ選択時、同一作者は1人としてカウント
   - 作者の識別は GitHub ユーザー名（可能であればメールアドレス）で行う
   - 週ごとに動的に再計算（キャッシュは個別リポジトリのみ）

5. **セキュリティ**
   - GitHub トークンは環境変数から読み込み
   - .env ファイルは .gitignore に追加
   - SQL インジェクション対策（SQLAlchemy 使用）

## 実装開始手順

1. まずプロジェクト構造とrequirements.txt を作成
2. 設定ファイルの読み込み機能を実装
3. データベースモデルとテーブル作成
4. GitHub API クライアントの基本実装
5. 週次集計ロジックの実装
6. 基本的なグラフ生成
7. CLI コマンドの実装
8. 順次機能を追加

## 成功基準

- 指定された複数リポジトリのデータを正確に取得できる
- 週次生産性と4週移動平均が正しく計算される
- タイムゾーン変換が正確に行われる
- 差分更新により効率的なデータ取得ができる
- 生成される HTML グラフが見やすく操作しやすい
- エラー時も適切にリカバリーできる

以上の仕様に基づいて、高品質で保守性の高いコードを実装してください。