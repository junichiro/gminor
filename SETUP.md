# セットアップガイド - GitHub 生産性メトリクス可視化ツール

## 必要な設定

### 1. GitHub Personal Access Token の取得

1. GitHub にログインし、Settings > Developer settings > Personal access tokens > Tokens (classic) へ移動
2. "Generate new token (classic)" をクリック
3. 必要なスコープ:
   - `repo` (プライベートリポジトリにアクセスする場合は必須)
   - `public_repo` (パブリックリポジトリのみの場合)

### 2. 環境変数の設定

```bash
# .env.example を .env にコピー
cp .env.example .env

# .env ファイルを編集して GitHub トークンを設定
# GITHUB_TOKEN=ghp_your_actual_token_here
```

### 3. 設定ファイルのカスタマイズ

`config.yaml` を編集して、対象リポジトリを設定：

```yaml
github:
  repositories:
    - "your-org/repo1"
    - "your-org/repo2"
    - "your-org/repo3"
```

## セキュリティ注意事項

- **絶対に `.env` ファイルをコミットしないでください**
- GitHub トークンは他人に共有しないでください
- 定期的にトークンをローテーションしてください
- 不要になったトークンは削除してください

## ディレクトリ構造

実行時に自動的に以下のディレクトリが作成されます：

```
./data/     # SQLite データベース
./logs/     # ログファイル
./output/   # HTML レポート出力
```

これらのディレクトリは `.gitignore` で除外されています。