# 設定ファイルセットアップガイド

## 概要
このプロジェクトでは、機密情報の安全性とユーザー設定の柔軟性を確保するため、設定を複数のファイルに分割管理しています。

## 設定ファイル構成

### 1. 環境変数ファイル (.env)
**機密情報を格納** - Gitにコミットされません

```bash
# .env.example をコピーして作成
cp .env.example .env
```

設定内容:
- GitHub Personal Access Token
- その他の機密情報

### 2. アプリケーション設定ファイル (config.yaml)
**ユーザー固有の設定を格納** - Gitにコミットされません

```bash
# config.yaml.example をコピーして作成
cp config.yaml.example config.yaml
```

設定内容:
- 監視対象リポジトリリスト
- タイムゾーン設定
- 出力設定
- その他の個人設定

## セットアップ手順

### ステップ 1: 環境変数の設定

1. `.env.example` を `.env` にコピー:
   ```bash
   cp .env.example .env
   ```

2. `.env` ファイルを編集し、GitHub トークンを設定:
   ```bash
   GITHUB_TOKEN=ghp_your_actual_token_here
   ```

### ステップ 2: アプリケーション設定

1. `config.yaml.example` を `config.yaml` にコピー:
   ```bash
   cp config.yaml.example config.yaml
   ```

2. `config.yaml` の `github.repositories` セクションを編集:
   ```yaml
   github:
     repositories:
       - "your-organization/backend-api"
       - "your-organization/frontend-app"
       - "your-username/personal-project"
   ```

3. 必要に応じてその他の設定を調整:
   ```yaml
   application:
     timezone: "Asia/Tokyo"  # あなたのタイムゾーン
     output:
       directory: "output"
       filename: "productivity_chart.html"
   ```

## セキュリティ上の注意事項

### 機密情報の管理
- **GitHub トークン**: 必ず `.env` ファイルに保存し、Gitにコミットしない
- **個人リポジトリ名**: `config.yaml` に記載し、Gitにコミットしない
- **組織の内部情報**: 設定ファイルに組織固有の情報を含めない

### .gitignore による保護
以下のファイルは自動的にGit管理から除外されます:
```
# User-specific configuration files
config.yaml

# Configuration files with secrets
.env
.env.local
.env.production
.env.development
.env.test
```

## トラブルシューティング

### よくあるエラー

1. **「環境変数 GITHUB_TOKEN を設定してください」エラー**
   - `.env` ファイルが存在するか確認
   - `.env` 内の `GITHUB_TOKEN` が正しく設定されているか確認

2. **「リポジトリが見つかりません」エラー**
   - `config.yaml` のリポジトリ名が正しいか確認
   - GitHub トークンに該当リポジトリへのアクセス権限があるか確認

3. **設定ファイルが読み込まれない**
   - ファイル名が正しいか確認 (`config.yaml`, `.env`)
   - YAML形式が正しいか確認 (インデント、コロンなど)

### 設定検証コマンド
```bash
# 設定を確認
python main.py config

# より詳細な設定情報
python main.py config --verbose
```

## 開発者向け情報

### テンプレートファイルの更新
新しい設定項目を追加する場合:

1. `config.yaml.example` にプレースホルダー値で追加
2. `.env.example` に必要に応じて環境変数を追加
3. このドキュメント（CONFIG_SETUP.md）を更新

### 設定ファイルの階層
1. **環境変数** (.env) - 最高優先度
2. **ユーザー設定** (config.yaml) - 中優先度
3. **デフォルト値** (コード内) - 最低優先度