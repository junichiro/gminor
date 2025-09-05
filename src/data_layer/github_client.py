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
from functools import wraps

from github import Github, GithubException, RateLimitExceededException, UnknownObjectException
import requests
from tqdm import tqdm

# ログ設定
logger = logging.getLogger(__name__)


def retry_on_rate_limit(max_retries: int = 3, backoff_factor: float = 1.0):
    """レート制限とネットワークエラー用のリトライデコレータ
    
    GitHub APIのレート制限やネットワークエラーに対して自動的にリトライを行います。
    レート制限の場合はリセットまで待機し、ネットワークエラーの場合は指数バックオフを使用します。
    
    Args:
        max_retries: 最大リトライ回数（デフォルト: 3）
        backoff_factor: ネットワークエラー時の指数バックオフ係数（デフォルト: 1.0）
        
    Returns:
        デコレータ関数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                    
                except RateLimitExceededException as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.info(
                            f"Rate limit exceeded for {func.__name__}, waiting for reset... "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        self.wait_for_rate_limit_reset()
                        continue
                    # 最後の試行で失敗した場合はRateLimitErrorとして再投げ
                    rate_limit_info = self._github.get_rate_limit().core
                    raise RateLimitError(
                        f"Rate limit exceeded after {max_retries} retries", 
                        reset_time=rate_limit_info.reset,
                        remaining=rate_limit_info.remaining
                    )
                    
                except requests.RequestException as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.info(
                            f"Network error in {func.__name__}: {e}, retrying in {wait_time} seconds... "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(wait_time)
                        continue
                    # 最後の試行で失敗した場合はGitHubAPIErrorとして再投げ
                    raise GitHubAPIError(
                        f"Network error after {max_retries} retries: {e}",
                        original_error=e
                    )
            
            # このポイントに到達することは通常ないが、安全のため
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


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
    """GitHub APIクライアント（レート制限対応・リトライ機能付き）
    
    PyGithubを使用してGitHub APIへの認証済みアクセスを提供します。
    マージ済みプルリクエストの取得、レート制限の自動制御、
    包括的なエラーハンドリング、および進捗表示機能を含みます。
    
    主要な機能:
    - 自動的な認証検証
    - レート制限の自動監視と待機
    - レート制限バッファによる事前制御
    - ネットワークエラーの自動リトライ（指数バックオフ）
    - tqdmによる進捗表示
    - 包括的なエラーハンドリングとログ出力
    - デコレータベースの透過的なリトライ処理
    
    使用例:
        client = GitHubClient(token="your_token", rate_limit_buffer=100)
        
        # 基本的な使用
        prs = client.fetch_merged_prs("owner/repo", since_date)
        
        # 進捗表示付き
        prs = client.fetch_merged_prs_with_progress("owner/repo", since_date)
        
        # レート制限状況の確認
        status = client.get_rate_limit_status()
    """
    
    def __init__(self, token: str, per_page: int = 100, timeout: int = 30, rate_limit_buffer: int = 100) -> None:
        """GitHubClientを初期化
        
        Args:
            token: GitHub認証トークン
            per_page: 1回のAPIコールで取得するアイテム数（デフォルト: 100）
            timeout: API接続タイムアウト秒数（デフォルト: 30）
            rate_limit_buffer: レート制限バッファ（デフォルト: 100）
            
        Raises:
            GitHubAPIError: トークンが空またはNoneの場合、初期化に失敗した場合
        """
        if not token:
            raise GitHubAPIError("Token cannot be empty")
        
        self._token = token
        self._per_page = per_page
        self._timeout = timeout
        self._rate_limit_buffer = rate_limit_buffer
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
    
    def wait_for_rate_limit_reset(self) -> None:
        """レート制限がリセットされるまで待機
        
        現在のレート制限状況を確認し、必要に応じてリセットまで待機します。
        リセット時刻が既に過去の場合は待機しません。
        レート制限情報の取得に失敗した場合は、デフォルトで1時間待機します。
        
        Raises:
            GitHubAPIError: 重大なAPIエラーが発生した場合（フォールバック待機後）
        """
        try:
            rate_limit_info = self._github.get_rate_limit().core
            reset_time = rate_limit_info.reset
            current_time = datetime.now(timezone.utc)
            remaining = rate_limit_info.remaining
            
            logger.info(f"Current rate limit status: {remaining}/{rate_limit_info.limit} remaining")
            
            if reset_time > current_time:
                # リセット時刻まで待機（60秒のバッファを追加）
                wait_seconds = int((reset_time - current_time).total_seconds() + 60)
                logger.info(
                    f"Rate limit reset required. Waiting {wait_seconds} seconds until {reset_time} "
                    f"(current: {current_time})"
                )
                
                # 長時間待機の場合は進捗表示
                if wait_seconds > 300:  # 5分以上
                    with tqdm(total=wait_seconds, desc="Waiting for rate limit reset", unit="s") as pbar:
                        for _ in range(wait_seconds):
                            time.sleep(1)
                            pbar.update(1)
                else:
                    time.sleep(wait_seconds)
                    
                logger.info("Rate limit wait completed")
            else:
                logger.debug("Rate limit reset time has already passed, no wait required")
                
        except GithubException as e:
            if e.status == 401:
                raise GitHubAPIError("Authentication failed during rate limit check")
            logger.warning(f"GitHub API error while checking rate limit: {e}")
            # 短めのフォールバック待機
            logger.info("Falling back to 10 minute wait")
            time.sleep(600)
            
        except requests.RequestException as e:
            logger.warning(f"Network error while checking rate limit: {e}")
            logger.info("Falling back to 10 minute wait")
            time.sleep(600)
            
        except Exception as e:
            logger.warning(f"Unexpected error while checking rate limit: {e}")
            # より長いフォールバック: 1時間待機
            logger.info("Falling back to 1 hour wait due to unexpected error")
            time.sleep(3600)
    
    def check_rate_limit_and_wait_if_needed(self) -> None:
        """レート制限バッファをチェックし、必要に応じて待機
        
        残りリクエスト数がバッファ値を下回る場合、自動的に待機します。
        重要なエラーは再発生させ、軽微なエラーのみログ出力します。
        """
        try:
            rate_status = self.get_rate_limit_status()
            remaining = rate_status["remaining"]
            
            if remaining < self._rate_limit_buffer:
                logger.warning(
                    f"Rate limit buffer threshold reached: {remaining}/{rate_status['limit']} remaining "
                    f"(buffer: {self._rate_limit_buffer}). Waiting for reset..."
                )
                self.wait_for_rate_limit_reset()
                
        except RateLimitExceededException as e:
            # レート制限エラーは重要なので再発生
            logger.error(f"Rate limit exceeded during buffer check: {e}")
            raise
            
        except GitHubAPIError as e:
            # GitHub APIエラーは重要なので再発生
            logger.error(f"GitHub API error during rate limit check: {e}")
            raise
            
        except Exception as e:
            # その他のエラーはログ出力のみ（処理継続）
            logger.warning(f"Non-critical error checking rate limit: {e}")
    
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
        return self._fetch_merged_prs_impl(repo, since, until, show_progress=False)
    
    def fetch_merged_prs_with_progress(self, repo: str, since: datetime, until: Optional[datetime] = None, 
                                     show_progress: bool = True) -> List[Dict[str, Any]]:
        """進捗表示付きで指定期間のマージ済みプルリクエストを取得
        
        Args:
            repo: リポジトリ名（"owner/repo"形式）
            since: 開始日時（UTC）
            until: 終了日時（UTC、Noneの場合は現在時刻）
            show_progress: 進捗バーを表示するかどうか
            
        Returns:
            List[Dict[str, Any]]: マージ済みPRのリスト
            
        Raises:
            GitHubAPIError: リポジトリが存在しない、または一般的なAPI エラー
            RateLimitError: レート制限に達した場合
        """
        return self._fetch_merged_prs_impl(repo, since, until, show_progress)
    
    def _fetch_merged_prs_impl(self, repo: str, since: datetime, until: Optional[datetime], show_progress: bool) -> List[Dict[str, Any]]:
        """マージ済みPR取得の実装（ページネーション対応・リトライ機能付き）
        
        Args:
            repo: リポジトリ名（"owner/repo"形式）
            since: 開始日時（UTC）
            until: 終了日時（UTC、Noneの場合は現在時刻）
            show_progress: 進捗バーを表示するかどうか
            
        Returns:
            List[Dict[str, Any]]: マージ済みPRのリスト
            
        Raises:
            GitHubAPIError: リポジトリが存在しない、または一般的なAPI エラー
            RateLimitError: レート制限に達した場合
        """
        if until is None:
            until = datetime.now(timezone.utc)
        
        progress_msg = "with progress display" if show_progress else "without progress display"
        logger.info(f"Fetching merged PRs for {repo} from {since} to {until} {progress_msg}")
        
        try:
            repository = self._github.get_repo(repo)
            
            # クローズされたPRを取得（マージされたものを含む）
            pulls = repository.get_pulls(
                state="closed",
                sort="updated", 
                direction="desc"
            )
            
            merged_prs = []
            
            # 進捗バー設定
            progress_desc = f"Processing PRs from {repo}"
            with tqdm(desc=progress_desc, unit="PR", disable=not show_progress) as pbar:
                for pr in pulls:
                    try:
                        # レート制限バッファチェック
                        self.check_rate_limit_and_wait_if_needed()
                        
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
                        if show_progress:
                            pbar.update(1)
                            pbar.set_postfix({"Found": len(merged_prs)})
                        
                        logger.debug(f"Found merged PR #{pr.number}: {pr.title}")
                        
                    except RateLimitExceededException as e:
                        logger.info(f"Rate limit exceeded while processing PR, waiting for reset...")
                        self.wait_for_rate_limit_reset()
                        # レート制限後は同じPRから継続（for文が自動的に次のPRに進む）
                        continue
                        
                    except requests.RequestException as e:
                        logger.warning(f"Network error while processing PR: {e}. Retrying...")
                        # ネットワークエラーの場合は短い待機後に継続
                        time.sleep(1)
                        continue
            
            logger.info(f"Found {len(merged_prs)} merged PRs for {repo}")
            return merged_prs
            
        except UnknownObjectException as e:
            error_msg = f"Repository not found: {repo}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
            
        except RateLimitExceededException as e:
            # 初期のリポジトリ取得やPRリスト取得で発生したレート制限
            rate_limit_info = self._github.get_rate_limit().core
            reset_time = rate_limit_info.reset
            remaining = rate_limit_info.remaining
            
            error_msg = f"Rate limit exceeded during initial repository access. Resets at: {reset_time}, Remaining: {remaining}"
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
                f"timeout={self._timeout}, rate_limit_buffer={self._rate_limit_buffer})")