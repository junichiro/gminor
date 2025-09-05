# セキュリティチェックリスト

## 設定ファイル作成後の確認事項

### 1. 機密情報の確認
- [ ] `.env` ファイルに実際のGitHubトークンを設定済み
- [ ] `config.yaml` に実際のリポジトリ名を設定済み
- [ ] 機密情報がGitにコミットされていないことを確認

### 2. .gitignore の動作確認
以下のコマンドで、設定ファイルがGit管理から除外されていることを確認:

```bash
# 除外ファイルの確認（何も出力されないはず）
git status --ignored | grep -E "\.(env|yaml)$"

# 設定ファイルが追跡されていないことを確認
git ls-files | grep -E "(config\.yaml|\.env)$"
```

### 3. 設定ファイルの動作テスト
```bash
# 設定の読み込みテスト
python main.py config

# 実際にAPIアクセスできるかテスト
python main.py stats
```

### 4. チーム共有前のチェック
新しいチームメンバーが以下を実行できることを確認:

```bash
# テンプレートファイルの存在確認
ls -la config.yaml.example .env.example

# セットアップガイドの確認
cat CONFIG_SETUP.md
```

## 緊急時の対応

### GitHubトークンの漏洩を発見した場合
1. **即座にGitHubでトークンを無効化**
2. 新しいトークンを生成
3. `.env` ファイルを更新
4. Git履歴に機密情報が含まれていないか確認

### 設定ファイルを誤ってコミットした場合
```bash
# 最新コミットから削除（まだプッシュしていない場合）
git rm --cached config.yaml
git commit --amend --no-edit

# 履歴から完全削除が必要な場合（注意：危険な操作）
git filter-branch --tree-filter 'rm -f config.yaml' HEAD
```

## 定期メンテナンス

### 月次チェック
- [ ] `.gitignore` が最新の設定ファイルパターンをカバーしているか
- [ ] テンプレートファイルが実際の設定項目と同期しているか
- [ ] GitHubトークンの有効期限確認（該当する場合）

### 新機能追加時
- [ ] 新しい設定項目は適切にテンプレート化されているか
- [ ] 機密情報を含む新しい設定は `.env` に分離されているか
- [ ] `.gitignore` に新しいパターンが必要か確認