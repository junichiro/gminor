# CLI使用方法

GitHub生産性メトリクス可視化ツール(gminor)のCLIコマンドの使用方法について説明します。

## セットアップ

### 1. 環境変数の設定

GitHub APIトークンを環境変数として設定する必要があります。

```bash
export GITHUB_TOKEN="your_github_personal_access_token_here"
```

### 2. 設定ファイルの確認

`config.yaml`ファイルの`github.repositories`セクションに、分析対象のリポジトリを追加してください。

```yaml
github:
  api_base_url: https://api.github.com
  timeout: 30
  repositories:
    - owner/repo1
    - owner/repo2
```

## 基本的なコマンド

### ヘルプの表示

```bash
python main.py --help
```

### initコマンド - 初回データ取得

GitHubからプルリクエストデータを取得し、データベースに保存します。

```bash
# デフォルトで過去180日分のデータを取得
python main.py init

# 過去90日分のデータを取得
python main.py init --days 90

# ヘルプの表示
python main.py init --help
```

#### 実行結果例

```
初期データ同期を開始しています...
✅ データ同期が完了しました！
📊 処理したリポジトリ数: 2
📋 取得したPR数: 150
⏱️  実行時間: 45.2秒
```

### visualizeコマンド - グラフ生成

データベースから週次メトリクスを読み込み、生産性グラフを生成します。

```bash
# グラフを生成
python main.py visualize

# ヘルプの表示
python main.py visualize --help
```

#### 実行結果例

```
📊 グラフ生成を開始しています...
📈 12週分のデータを可視化します...
✅ グラフが正常に生成されました: output/productivity_chart.html
🌐 ブラウザで開いてご確認ください。
```

## ディレクトリ構成

実行後に以下のディレクトリとファイルが作成されます：

```
gminor/
├── data/
│   └── gminor_db.sqlite      # SQLiteデータベース
├── output/
│   └── productivity_chart.html # 生成されたグラフ
└── logs/                     # ログファイル（設定に応じて）
```

## エラーハンドリング

### 一般的なエラーと解決方法

1. **GitHub APIトークンが設定されていない**
   ```
   GitHub APIトークンが設定されていません。
   環境変数 GITHUB_TOKEN を設定してください。
   ```
   → 環境変数`GITHUB_TOKEN`を設定してください

2. **設定ファイルにリポジトリが定義されていない**
   ```
   設定ファイルにリポジトリが定義されていません。
   config.yaml の github.repositories に対象リポジトリを追加してください。
   ```
   → `config.yaml`の`github.repositories`にリポジトリを追加してください

3. **データベースファイルが見つからない（visualizeコマンド）**
   ```
   データベースファイルが見つかりません: data/gminor_db.sqlite
   まず 'init' コマンドを実行してデータを取得してください。
   ```
   → 先に`init`コマンドを実行してください

## 推奨ワークフロー

1. **初回セットアップ**
   ```bash
   # 環境変数設定
   export GITHUB_TOKEN="your_token"
   
   # データ取得
   python main.py init
   ```

2. **定期的な更新**
   ```bash
   # 新しいデータを取得（増分更新は未実装のため、再度initを実行）
   python main.py init --days 30
   
   # グラフ更新
   python main.py visualize
   ```

3. **データ確認**
   - `output/productivity_chart.html`をブラウザで開く
   - 週次生産性の推移を確認

## トラブルシューティング

### ログの確認

設定に応じてログファイルが出力されます。エラーの詳細はログを確認してください。

### データベースのリセット

データベースをリセットしたい場合は、`data/`ディレクトリを削除して再度`init`コマンドを実行してください。

```bash
rm -rf data/
python main.py init
```

### 権限エラー

`data/`や`output/`ディレクトリに書き込み権限があることを確認してください。

## 高度な使用方法

### 複数リポジトリの分析

`config.yaml`に複数のリポジトリを設定することで、複数のプロジェクトの生産性を同時に分析できます。

```yaml
github:
  repositories:
    - organization/backend-api
    - organization/frontend-app
    - organization/mobile-app
```

### タイムゾーンの設定

アプリケーション設定でタイムゾーンを変更できます。

```yaml
application:
  name: gminor
  version: 1.0.0
  environment: development
  timezone: America/New_York  # デフォルト: Asia/Tokyo
```