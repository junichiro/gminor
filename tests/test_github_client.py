"""GitHub APIクライアントのテスト"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.data_layer.github_client import (
    GitHubClient,
    GitHubAPIError,
    RateLimitError
)


class TestGitHubClientExceptions:
    """GitHub APIクライアントのカスタム例外テスト"""
    
    def test_GitHubAPIErrorが正常に作成される(self):
        """正常系: GitHubAPIError例外が正常に作成されることを確認"""
        error_msg = "GitHub API error occurred"
        error = GitHubAPIError(error_msg)
        assert str(error) == error_msg
        assert isinstance(error, Exception)
    
    def test_RateLimitErrorがGitHubAPIErrorを継承している(self):
        """正常系: RateLimitErrorがGitHubAPIErrorを継承していることを確認"""
        error_msg = "Rate limit exceeded"
        error = RateLimitError(error_msg)
        assert str(error) == error_msg
        assert isinstance(error, GitHubAPIError)
        assert isinstance(error, Exception)


class TestGitHubClientInitialization:
    """GitHubClientクラスの初期化テスト"""
    
    def test_GitHubClientが正常に初期化される(self):
        """正常系: 有効なトークンでGitHubClientが初期化されることを確認"""
        token = "test_token_123"
        client = GitHubClient(token)
        assert client is not None
    
    def test_GitHubClientの初期化で空トークンはエラーになる(self):
        """異常系: 空のトークンでGitHubAPIErrorが発生することを確認"""
        with pytest.raises(GitHubAPIError, match="Token cannot be empty"):
            GitHubClient("")
    
    def test_GitHubClientの初期化でNoneトークンはエラーになる(self):
        """異常系: Noneトークンでエラーが発生することを確認"""
        with pytest.raises(GitHubAPIError, match="Token cannot be empty"):
            GitHubClient(None)
    
    @patch('src.data_layer.github_client.Github')
    def test_GitHubClientの初期化でPyGithubが呼ばれる(self, mock_github):
        """正常系: 初期化時にPyGithubのGithubクラスが呼ばれることを確認"""
        token = "test_token_123"
        GitHubClient(token)
        mock_github.assert_called_once_with(token)


class TestGitHubClientAuthentication:
    """GitHubClientの認証テスト"""
    
    @patch('src.data_layer.github_client.Github')
    def test_認証が正常に動作する(self, mock_github):
        """正常系: GitHub APIの認証が正常に動作することを確認"""
        # モックの設定
        mock_github_instance = Mock()
        mock_user = Mock()
        mock_user.login = "test_user"
        mock_github_instance.get_user.return_value = mock_user
        mock_github.return_value = mock_github_instance
        
        token = "valid_token"
        client = GitHubClient(token)
        
        # 認証確認のために現在のユーザー情報を取得
        user_info = client._verify_authentication()
        
        assert user_info == "test_user"
        mock_github_instance.get_user.assert_called_once()
    
    @patch('src.data_layer.github_client.Github')
    def test_認証失敗時にGitHubAPIErrorが発生する(self, mock_github):
        """異常系: 認証失敗時にGitHubAPIErrorが発生することを確認"""
        from github import GithubException
        
        # モックの設定
        mock_github_instance = Mock()
        mock_github_instance.get_user.side_effect = GithubException(401, "Bad credentials")
        mock_github.return_value = mock_github_instance
        
        token = "invalid_token"
        client = GitHubClient(token)
        
        with pytest.raises(GitHubAPIError, match="Authentication failed"):
            client._verify_authentication()


class TestFetchMergedPRs:
    """fetch_merged_prsメソッドのテスト"""
    
    @patch('src.data_layer.github_client.Github')
    def test_マージ済みPR取得が正常に動作する(self, mock_github):
        """正常系: 指定期間のマージ済みPRが正常に取得されることを確認"""
        # モックPRデータの準備
        mock_pr1 = Mock()
        mock_pr1.number = 123
        mock_pr1.title = "Feature PR 1"
        mock_pr1.user.login = "developer1"
        mock_pr1.merged_at = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        mock_pr1.created_at = datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc)
        mock_pr1.updated_at = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        
        mock_pr2 = Mock()
        mock_pr2.number = 124
        mock_pr2.title = "Feature PR 2"
        mock_pr2.user.login = "developer2"
        mock_pr2.merged_at = datetime(2024, 1, 16, 14, 15, tzinfo=timezone.utc)
        mock_pr2.created_at = datetime(2024, 1, 11, 8, 30, tzinfo=timezone.utc)
        mock_pr2.updated_at = datetime(2024, 1, 16, 14, 15, tzinfo=timezone.utc)
        
        # モックリポジトリの設定
        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pr1, mock_pr2]
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        # テスト実行
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = client.fetch_merged_prs("owner/repo", since_date, until_date)
        
        # アサーション
        assert len(result) == 2
        
        assert result[0]["number"] == 123
        assert result[0]["title"] == "Feature PR 1"
        assert result[0]["author"] == "developer1"
        assert result[0]["merged_at"] == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        
        assert result[1]["number"] == 124
        assert result[1]["title"] == "Feature PR 2"
        assert result[1]["author"] == "developer2"
        assert result[1]["merged_at"] == datetime(2024, 1, 16, 14, 15, tzinfo=timezone.utc)
        
        # モックが正しく呼ばれたことを確認
        mock_github_instance.get_repo.assert_called_once_with("owner/repo")
        mock_repo.get_pulls.assert_called_once_with(
            state="closed", 
            sort="updated", 
            direction="desc"
        )
    
    @patch('src.data_layer.github_client.Github')
    def test_until日時がNoneの場合現在時刻が使用される(self, mock_github):
        """正常系: until日時がNoneの場合、現在時刻が使用されることを確認"""
        mock_repo = Mock()
        mock_repo.get_pulls.return_value = []
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        with patch('src.data_layer.github_client.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 31, 12, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            result = client.fetch_merged_prs("owner/repo", since_date, None)
            
            # 現在時刻が取得されることを確認
            mock_datetime.now.assert_called_once_with(timezone.utc)
    
    @patch('src.data_layer.github_client.Github')
    def test_マージされていないPRは除外される(self, mock_github):
        """正常系: マージされていないPRは結果に含まれないことを確認"""
        # マージされていないPR
        mock_pr_open = Mock()
        mock_pr_open.merged_at = None
        mock_pr_open.state = "closed"
        
        # マージされたPR
        mock_pr_merged = Mock()
        mock_pr_merged.number = 125
        mock_pr_merged.title = "Merged PR"
        mock_pr_merged.user.login = "developer3"
        mock_pr_merged.merged_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
        mock_pr_merged.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_pr_merged.updated_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
        
        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pr_open, mock_pr_merged]
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = client.fetch_merged_prs("owner/repo", since_date, until_date)
        
        # マージされたPRのみが含まれることを確認
        assert len(result) == 1
        assert result[0]["number"] == 125
    
    @patch('src.data_layer.github_client.Github')
    def test_期間外のPRは除外される(self, mock_github):
        """正常系: 指定期間外のPRは結果に含まれないことを確認"""
        # 期間より前のPR
        mock_pr_before = Mock()
        mock_pr_before.merged_at = datetime(2023, 12, 31, tzinfo=timezone.utc)
        
        # 期間内のPR
        mock_pr_within = Mock()
        mock_pr_within.number = 126
        mock_pr_within.title = "Within Range PR"
        mock_pr_within.user.login = "developer4"
        mock_pr_within.merged_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_pr_within.created_at = datetime(2024, 1, 10, tzinfo=timezone.utc)
        mock_pr_within.updated_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        
        # 期間より後のPR
        mock_pr_after = Mock()
        mock_pr_after.merged_at = datetime(2024, 2, 1, tzinfo=timezone.utc)
        
        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pr_before, mock_pr_within, mock_pr_after]
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = client.fetch_merged_prs("owner/repo", since_date, until_date)
        
        # 期間内のPRのみが含まれることを確認
        assert len(result) == 1
        assert result[0]["number"] == 126
    
    @patch('src.data_layer.github_client.Github')
    def test_リポジトリが存在しない場合GitHubAPIErrorが発生する(self, mock_github):
        """異常系: リポジトリが存在しない場合GitHubAPIErrorが発生することを確認"""
        from github import UnknownObjectException
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.side_effect = UnknownObjectException(404, "Not Found")
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        with pytest.raises(GitHubAPIError, match="Repository not found"):
            client.fetch_merged_prs("owner/nonexistent", since_date, until_date)


class TestRateLimitHandling:
    """レート制限処理のテスト"""
    
    @patch('src.data_layer.github_client.Github')
    def test_get_rate_limit_statusが正常に動作する(self, mock_github):
        """正常系: レート制限状態が正常に取得されることを確認"""
        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 4500
        mock_rate_limit.core.reset = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        
        mock_github_instance = Mock()
        mock_github_instance.get_rate_limit.return_value = mock_rate_limit
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        result = client.get_rate_limit_status()
        
        expected = {
            "limit": 5000,
            "remaining": 4500,
            "reset": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        }
        assert result == expected
        mock_github_instance.get_rate_limit.assert_called_once()
    
    @patch('src.data_layer.github_client.Github')
    def test_レート制限に達した場合RateLimitErrorが発生する(self, mock_github):
        """異常系: レート制限に達した場合RateLimitErrorが発生することを確認"""
        from github import RateLimitExceededException
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.side_effect = RateLimitExceededException(
            403, "Rate limit exceeded"
        )
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            client.fetch_merged_prs("owner/repo", since_date, until_date)
    
    @patch('src.data_layer.github_client.Github')
    def test_レート制限取得でエラーが発生した場合GitHubAPIErrorになる(self, mock_github):
        """異常系: レート制限取得エラー時にGitHubAPIErrorが発生することを確認"""
        from github import GithubException
        
        mock_github_instance = Mock()
        mock_github_instance.get_rate_limit.side_effect = GithubException(500, "Server Error")
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        
        with pytest.raises(GitHubAPIError, match="Failed to get rate limit status"):
            client.get_rate_limit_status()


class TestGitHubClientErrorHandling:
    """GitHubClientのエラーハンドリングテスト"""
    
    @patch('src.data_layer.github_client.Github')
    def test_一般的なGitHub例外はGitHubAPIErrorに変換される(self, mock_github):
        """異常系: 一般的なGitHub例外がGitHubAPIErrorに変換されることを確認"""
        from github import GithubException
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.side_effect = GithubException(500, "Internal Server Error")
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        with pytest.raises(GitHubAPIError, match="GitHub API error"):
            client.fetch_merged_prs("owner/repo", since_date, until_date)
    
    @patch('src.data_layer.github_client.Github')
    def test_ネットワークエラーはGitHubAPIErrorに変換される(self, mock_github):
        """異常系: ネットワークエラーがGitHubAPIErrorに変換されることを確認"""
        import requests
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.side_effect = requests.RequestException("Connection failed")
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient("test_token")
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        with pytest.raises(GitHubAPIError, match="Network error"):
            client.fetch_merged_prs("owner/repo", since_date, until_date)


class TestGitHubClientIntegration:
    """GitHubClientの統合テスト"""
    
    @patch('src.data_layer.github_client.Github')
    def test_完全なワークフローが動作する(self, mock_github):
        """統合テスト: GitHubClientの完全なワークフローが動作することを確認"""
        # マージされたPRのモックデータ
        mock_pr = Mock()
        mock_pr.number = 100
        mock_pr.title = "Integration Test PR"
        mock_pr.user.login = "test_user"
        mock_pr.merged_at = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        mock_pr.created_at = datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc)
        mock_pr.updated_at = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        
        # レート制限のモックデータ
        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 4999
        mock_rate_limit.core.reset = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        
        # モックの設定
        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pr]
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_instance.get_rate_limit.return_value = mock_rate_limit
        mock_github.return_value = mock_github_instance
        
        # テスト実行
        client = GitHubClient("integration_test_token")
        
        # PR取得テスト
        since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        prs = client.fetch_merged_prs("test/repo", since_date, until_date)
        
        # レート制限状態取得テスト
        rate_status = client.get_rate_limit_status()
        
        # アサーション
        assert len(prs) == 1
        assert prs[0]["number"] == 100
        assert prs[0]["title"] == "Integration Test PR"
        
        assert rate_status["limit"] == 5000
        assert rate_status["remaining"] == 4999
        
        # 全ての必要なメソッドが呼ばれたことを確認
        mock_github_instance.get_repo.assert_called_once_with("test/repo")
        mock_github_instance.get_rate_limit.assert_called_once()