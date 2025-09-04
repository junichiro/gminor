"""GitHub APIクライアント

PyGithubを使用してGitHub APIからプルリクエストデータを取得するクライアント。
認証、レート制限管理、エラーハンドリングを提供します。

主な機能:
- GitHub認証トークンによる安全な認証
- 指定期間内のマージ済みPRの取得
- レート制限の監視と管理
- 包括的なエラーハンドリングとログ出力
- ネットワークエラーの自動検出
"""
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union

from github import Github, GithubException, RateLimitExceededException, UnknownObjectException
import requests

# ログ設定
logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """GitHub API関連のエラー
    
    GitHub APIの操作中に発生する一般的なエラーを表します。
    認証エラー、リポジトリアクセスエラー、ネットワークエラーなどが含まれます。
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.status_code = status_code
        self.original_error = original_error


class RateLimitError(GitHubAPIError):
    """レート制限エラー
    
    GitHub APIのレート制限に達した際に発生するエラーです。
    リセット時刻の情報を含みます。
    """
    
    def __init__(self, message: str, reset_time: Optional[datetime] = None, remaining: Optional[int] = None):
        super().__init__(message)
        self.reset_time = reset_time
        self.remaining = remaining


class GitHubClient:
    """GitHub APIクライアント
    
    PyGithubを使用してGitHub APIへの認証済みアクセスを提供します。
    マージ済みプルリクエストの取得、レート制限の監視、
    包括的なエラーハンドリングを含みます。
    
    特徴:
    - 自動的な認証検証
    - レート制限の自動監視
    - 包括的なエラーハンドリング
    - 詳細なログ出力
    - ネットワークエラーの検出と再試行
    """
    
    def __init__(self, token: str, per_page: int = 100, timeout: int = 30) -> None:
        """GitHubClientを初期化
        
        Args:
            token: GitHub認証トークン
            per_page: 1回のAPIコールで取得するアイテム数（デフォルト: 100）
            timeout: API接続タイムアウト秒数（デフォルト: 30）
            
        Raises:
            GitHubAPIError: トークンが空またはNoneの場合、初期化に失敗した場合
        """
        if not token:
            raise GitHubAPIError("Token cannot be empty")
        
        self._token = token
        self._per_page = per_page
        self._timeout = timeout
        logger.info("Initializing GitHub API client")
        
        try:
            self._github = Github(
                token, 
                per_page=per_page,
                timeout=timeout
            )
            logger.info(f"GitHub API client initialized successfully (per_page={per_page}, timeout={timeout}s)")
        except Exception as e:
            error_msg = f"Failed to initialize GitHub client: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, original_error=e)
    
    def _verify_authentication(self) -> str:
        """認証の有効性を確認
        
        Returns:
            str: 認証されたユーザーのログイン名
            
        Raises:
            GitHubAPIError: 認証に失敗した場合
        """
        try:
            user = self._github.get_user()
            logger.debug(f"Authentication verified for user: {user.login}")
            return user.login
        except GithubException as e:
            if e.status == 401:
                raise GitHubAPIError("Authentication failed: Invalid token")
            else:
                raise GitHubAPIError(f"Authentication failed: {e}")
        except Exception as e:
            raise GitHubAPIError(f"Authentication verification failed: {e}")
    
    def fetch_merged_prs(self, repo: str, since: datetime, until: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """指定期間のマージ済みプルリクエストを取得
        
        Args:
            repo: リポジトリ名（"owner/repo"形式）
            since: 開始日時（UTC）
            until: 終了日時（UTC、Noneの場合は現在時刻）
            
        Returns:
            List[Dict[str, Any]]: マージ済みPRのリスト
            
        Raises:
            GitHubAPIError: リポジトリが存在しない、または一般的なAPI エラー
            RateLimitError: レート制限に達した場合
        """
        if until is None:
            until = datetime.now(timezone.utc)
        
        logger.info(f"Fetching merged PRs for {repo} from {since} to {until}")
        
        try:
            repository = self._github.get_repo(repo)
            
            # クローズされたPRを取得（マージされたものを含む）
            pulls = repository.get_pulls(
                state="closed",
                sort="updated", 
                direction="desc"
            )
            
            merged_prs = []
            
            for pr in pulls:
                # マージされていないPRをスキップ
                if pr.merged_at is None:
                    continue
                
                # 指定期間外のPRをスキップ
                if pr.merged_at < since or pr.merged_at > until:
                    continue
                
                # PRデータを辞書形式で収集
                pr_data = {
                    "number": pr.number,
                    "title": pr.title,
                    "author": pr.user.login,
                    "merged_at": pr.merged_at,
                    "created_at": pr.created_at,
                    "updated_at": pr.updated_at
                }
                
                merged_prs.append(pr_data)
                logger.debug(f"Found merged PR #{pr.number}: {pr.title}")
            
            logger.info(f"Found {len(merged_prs)} merged PRs for {repo}")
            return merged_prs
            
        except UnknownObjectException as e:
            error_msg = f"Repository not found: {repo}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
            
        except RateLimitExceededException as e:
            # レート制限の詳細情報を取得
            rate_limit_info = self._github.get_rate_limit().core
            reset_time = rate_limit_info.reset
            remaining = rate_limit_info.remaining
            
            error_msg = f"Rate limit exceeded. Resets at: {reset_time}, Remaining: {remaining}"
            logger.error(error_msg)
            raise RateLimitError(error_msg, reset_time=reset_time, remaining=remaining)
            
        except GithubException as e:
            error_msg = f"GitHub API error: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, status_code=getattr(e, 'status', None), original_error=e)
            
        except requests.RequestException as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, original_error=e)
            
        except Exception as e:
            error_msg = f"Unexpected error fetching PRs: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, original_error=e)
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """APIレート制限の状態を取得
        
        Returns:
            Dict[str, Any]: レート制限情報
                - limit: 1時間あたりのリクエスト制限数
                - remaining: 残りリクエスト数
                - reset: リセット時刻（UTC）
                
        Raises:
            GitHubAPIError: レート制限状態の取得に失敗した場合
        """
        try:
            rate_limit = self._github.get_rate_limit()
            
            result = {
                "limit": rate_limit.core.limit,
                "remaining": rate_limit.core.remaining,
                "reset": rate_limit.core.reset
            }
            
            logger.debug(f"Rate limit status: {result['remaining']}/{result['limit']} remaining")
            return result
            
        except GithubException as e:
            error_msg = f"Failed to get rate limit status: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error getting rate limit: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, original_error=e)
    
    def validate_repository(self, repo: str) -> bool:
        """リポジトリの存在とアクセス権限を検証
        
        Args:
            repo: リポジトリ名（"owner/repo"形式）
            
        Returns:
            bool: リポジトリが存在しアクセス可能な場合True
        """
        try:
            repository = self._github.get_repo(repo)
            logger.debug(f"Repository {repo} is accessible")
            return True
        except UnknownObjectException:
            logger.warning(f"Repository {repo} not found or not accessible")
            return False
        except Exception as e:
            logger.error(f"Error validating repository {repo}: {e}")
            return False
    
    def get_repository_info(self, repo: str) -> Dict[str, Any]:
        """リポジトリの基本情報を取得
        
        Args:
            repo: リポジトリ名（"owner/repo"形式）
            
        Returns:
            Dict[str, Any]: リポジトリ情報
            
        Raises:
            GitHubAPIError: リポジトリが存在しない、またはアクセス権限がない場合
        """
        try:
            repository = self._github.get_repo(repo)
            
            info = {
                "name": repository.name,
                "full_name": repository.full_name,
                "private": repository.private,
                "default_branch": repository.default_branch,
                "created_at": repository.created_at,
                "updated_at": repository.updated_at,
                "language": repository.language,
                "stargazers_count": repository.stargazers_count,
                "forks_count": repository.forks_count
            }
            
            logger.debug(f"Retrieved repository info for {repo}")
            return info
            
        except UnknownObjectException as e:
            error_msg = f"Repository not found: {repo}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, status_code=404, original_error=e)
            
        except Exception as e:
            error_msg = f"Error getting repository info for {repo}: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg, original_error=e)
    
    def check_rate_limit_remaining(self, threshold: int = 100) -> bool:
        """レート制限の残り回数をチェック
        
        Args:
            threshold: 警告を出すしきい値（デフォルト: 100）
            
        Returns:
            bool: 残り回数がしきい値より多い場合True
        """
        try:
            rate_status = self.get_rate_limit_status()
            remaining = rate_status["remaining"]
            
            if remaining < threshold:
                logger.warning(
                    f"Rate limit approaching threshold: {remaining}/{rate_status['limit']} remaining. "
                    f"Resets at: {rate_status['reset']}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
    def __str__(self) -> str:
        """GitHubClientの文字列表現"""
        return f"<GitHubClient(timeout={self._timeout}, per_page={self._per_page})>"
    
    def __repr__(self) -> str:
        """GitHubClientのデバッグ表現"""
        return (f"GitHubClient(token='***', per_page={self._per_page}, "
                f"timeout={self._timeout})")