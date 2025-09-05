"""
データ同期機能を担当するモジュール（初回同期・差分同期・期間指定同期）
"""
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import logging

from ..data_layer.github_client import GitHubClient, GitHubAPIError
from ..data_layer.database_manager import DatabaseManager, DatabaseError
from ..data_layer.models import PullRequest, WeeklyMetrics, SyncStatus
from .aggregator import ProductivityAggregator


class DataSyncError(Exception):
    """データ同期エラー"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        データ同期エラーを初期化
        
        Args:
            message: エラーメッセージ
            original_error: 元のエラー（存在する場合）
        """
        super().__init__(message)
        self.original_error = original_error


class SyncManager:
    """初回データ同期を管理するクラス"""
    
    def __init__(self, github_client: GitHubClient, db_manager: DatabaseManager, 
                 aggregator: ProductivityAggregator):
        """
        SyncManagerを初期化
        
        Args:
            github_client: GitHubAPIクライアント
            db_manager: データベースマネージャー
            aggregator: 生産性集計処理クラス
        """
        self.github_client = github_client
        self.db_manager = db_manager
        self.aggregator = aggregator
        self.logger = logging.getLogger(__name__)
    
    def initial_sync(self, repositories: List[str], days_back: int = 180, 
                    progress: bool = False) -> Dict[str, Any]:
        """
        初回データ同期を実行
        
        Args:
            repositories: 同期対象のリポジトリリスト
            days_back: 過去何日分のデータを取得するか
            progress: プログレス表示するかどうか
            
        Returns:
            同期結果を含む辞書
            
        Raises:
            DataSyncError: 同期処理でエラーが発生した場合
        """
        start_time = time.time()
        
        self.logger.info(f"Starting initial sync for {len(repositories)} repositories, {days_back} days back")
        self.logger.debug(f"Target repositories: {repositories}")
        
        if not repositories:
            self.logger.warning("No repositories specified for sync")
            return self._create_sync_result(0, 0, start_time, [])
        
        try:
            since_date = self._calculate_since_date(days_back)
            self.logger.info(f"Sync period: {since_date} to {datetime.now(timezone.utc)}")
            
            total_prs_fetched, processed_repositories, failed_repositories = self._process_repositories(
                repositories, since_date, progress
            )
            
            if progress:
                self._display_completion_message(processed_repositories, failed_repositories)
            
            result = self._create_sync_result(
                processed_repositories, total_prs_fetched, start_time, failed_repositories
            )
            
            duration = result['sync_duration_seconds']
            self.logger.info(f"Initial sync completed in {duration:.2f} seconds: {result['status']}")
            self.logger.info(f"Summary: {processed_repositories} successful, {len(failed_repositories)} failed, {total_prs_fetched} PRs fetched")
            
            return result
        
        except DatabaseError as e:
            self.logger.error(f"Database error during sync: {e}")
            raise DataSyncError(f"Database error during sync: {e}", e)
        
        except Exception as e:
            self.logger.error(f"Unexpected error during sync: {e}")
            raise DataSyncError(f"Unexpected error during sync: {e}", e)
    
    def _calculate_since_date(self, days_back: int) -> datetime:
        """取得開始日を計算"""
        return datetime.now(timezone.utc) - timedelta(days=days_back)
    
    def _process_repositories(self, repositories: List[str], since_date: datetime, 
                            progress: bool) -> Tuple[int, int, List[str]]:
        """
        リポジトリリストを処理（エラー時も他のリポジトリは継続処理）
        
        Returns:
            Tuple[取得したPR総数, 処理成功したリポジトリ数, 失敗したリポジトリリスト]
        """
        total_prs_fetched = 0
        processed_repositories = 0
        failed_repositories = []
        
        for i, repository in enumerate(repositories):
            if progress:
                self._display_progress_message(i + 1, len(repositories), repository)
            
            try:
                prs_count = self._process_single_repository(repository, since_date)
                total_prs_fetched += prs_count
                processed_repositories += 1
                
            except (GitHubAPIError, Exception) as e:
                error_message = f"Error processing {repository}: {e}"
                self.logger.error(error_message)
                self._update_sync_status(repository, 'error', str(e))
                failed_repositories.append(repository)
                # エラーが発生しても他のリポジトリの処理は継続
                continue
        
        return total_prs_fetched, processed_repositories, failed_repositories
    
    def _process_single_repository(self, repository: str, since_date: datetime) -> int:
        """
        単一リポジトリを処理
        
        Returns:
            取得したPR数
        """
        # GitHubからPRデータを取得
        pr_data = self.github_client.fetch_merged_prs(repo=repository, since=since_date)
        
        if not pr_data:
            self._update_sync_status(repository, 'completed')
            return 0
        
        # データベースに保存（重複チェック付き）
        saved_prs = self._save_pr_data(repository, pr_data)
        
        # 週次メトリクスを計算・保存
        if saved_prs:
            weekly_metrics = self.aggregator.calculate_weekly_metrics(pr_data)
            self._save_weekly_metrics(repository, weekly_metrics)
        
        # SyncStatusを更新
        self._update_sync_status(repository, 'completed')
        
        return len(saved_prs)
    
    def _create_sync_result(self, processed_repositories: int, total_prs_fetched: int, 
                          start_time: float, failed_repositories: List[str]) -> Dict[str, Any]:
        """同期結果を作成"""
        status = 'success' if not failed_repositories else 'partial_success'
        
        result = {
            'status': status,
            'processed_repositories': processed_repositories,
            'total_prs_fetched': total_prs_fetched,
            'sync_duration_seconds': time.time() - start_time
        }
        
        if failed_repositories:
            result['failed_repositories'] = failed_repositories
            result['failed_count'] = len(failed_repositories)
        
        return result
    
    def _display_progress_message(self, current: int, total: int, repository: str) -> None:
        """プログレス表示メッセージを表示"""
        self.logger.info(f"Processing repository {current}/{total}: {repository}")
    
    def _display_completion_message(self, processed_repositories: int, 
                                  failed_repositories: List[str]) -> None:
        """完了メッセージを表示"""
        if not failed_repositories:
            self.logger.info(f"Successfully completed synchronization of {processed_repositories} repositories")
        else:
            self.logger.warning(
                f"Completed synchronization with {processed_repositories} successful, "
                f"{len(failed_repositories)} failed: {failed_repositories}"
            )
    
    def _save_pr_data(self, repository: str, pr_data: List[Dict[str, Any]]) -> List[PullRequest]:
        """
        PRデータをデータベースに保存（重複チェック付き、一括操作で最適化）
        
        Args:
            repository: リポジトリ名
            pr_data: PRデータのリスト
            
        Returns:
            保存されたPRオブジェクトのリスト
        """
        if not pr_data:
            return []
        
        saved_prs = []
        
        with self.db_manager.get_session() as session:
            # 一括重複チェック：該当するPR番号のリストを一度に取得
            pr_numbers = [pr_info["number"] for pr_info in pr_data]
            existing_prs = session.query(PullRequest.pr_number).filter(
                PullRequest.repo_name == repository,
                PullRequest.pr_number.in_(pr_numbers)
            ).all()
            existing_pr_numbers = {pr.pr_number for pr in existing_prs}
            
            # 新しいPRのみを一括作成
            for pr_info in pr_data:
                if pr_info["number"] not in existing_pr_numbers:
                    pr = PullRequest(
                        repo_name=repository,
                        pr_number=pr_info["number"],
                        author=pr_info["author"],
                        title=pr_info["title"],
                        merged_at=pr_info["merged_at"],
                        created_at=pr_info["created_at"],
                        updated_at=pr_info["updated_at"]
                    )
                    saved_prs.append(pr)
            
            # 一括保存
            if saved_prs:
                session.add_all(saved_prs)
                session.commit()
                self.logger.info(f"Saved {len(saved_prs)} new PRs for repository {repository}")
        
        return saved_prs
    
    def _save_weekly_metrics(self, repository: str, weekly_metrics_df) -> None:
        """
        週次メトリクスをデータベースに保存（一括操作で最適化）
        
        Args:
            repository: リポジトリ名
            weekly_metrics_df: 週次メトリクスのDataFrame
        """
        if weekly_metrics_df.empty:
            return
        
        with self.db_manager.get_session() as session:
            # 一括重複チェック
            week_dates = [row['week_start'].date() for _, row in weekly_metrics_df.iterrows()]
            existing_metrics = session.query(WeeklyMetrics.week_start_date).filter(
                WeeklyMetrics.repo_name == repository,
                WeeklyMetrics.week_start_date.in_(week_dates)
            ).all()
            existing_week_dates = {metrics.week_start_date for metrics in existing_metrics}
            
            # 新しいメトリクスのみを一括作成
            new_metrics = []
            for _, row in weekly_metrics_df.iterrows():
                week_date = row['week_start'].date()
                if week_date not in existing_week_dates:
                    metrics = WeeklyMetrics(
                        repo_name=repository,
                        week_start_date=week_date,
                        pr_count=row['pr_count'],
                        merged_pr_count=row['pr_count'],  # 集計済みデータはすべてマージ済み
                        total_authors=row['unique_authors']
                    )
                    new_metrics.append(metrics)
            
            # 一括保存
            if new_metrics:
                session.add_all(new_metrics)
                session.commit()
                self.logger.info(f"Saved {len(new_metrics)} weekly metrics for repository {repository}")
    
    def _update_sync_status(self, repository: str, status: str, 
                          error_message: Optional[str] = None) -> None:
        """
        同期ステータスを更新（legacy interface、内部でupdate_sync_statusを使用）
        
        Args:
            repository: リポジトリ名
            status: 同期ステータス
            error_message: エラーメッセージ（エラー時のみ）
        """
        if status == 'completed':
            self.update_sync_status(repository, {'success': True})
        elif status == 'error':
            self.update_sync_status(repository, {'success': False, 'error_message': error_message or 'Unknown error'})
        else:
            # その他のステータス（'in_progress'等）は直接処理
            with self.db_manager.get_session() as session:
                sync_status = session.query(SyncStatus).filter_by(
                    repo_name=repository
                ).first()
                
                if not sync_status:
                    sync_status = SyncStatus(repo_name=repository)
                    session.add(sync_status)
                
                sync_status.status = status
                sync_status.last_synced_at = datetime.now(timezone.utc)
                
                session.commit()
    
    def update_sync(self, repositories: List[str]) -> Dict[str, Any]:
        """
        差分データ同期を実行
        
        Args:
            repositories: 同期対象のリポジトリリスト
            
        Returns:
            同期結果を含む辞書
            
        Raises:
            DataSyncError: 同期処理でエラーが発生した場合
        """
        start_time = time.time()
        
        if not repositories:
            return self._create_sync_result(0, 0, start_time, [])
        
        try:
            total_prs_fetched, processed_repositories, failed_repositories = self._process_repositories_incremental(
                repositories
            )
            
            return self._create_sync_result(
                processed_repositories, total_prs_fetched, start_time, failed_repositories
            )
        
        except DatabaseError as e:
            self.logger.error(f"Database error during incremental sync: {e}")
            raise DataSyncError(f"Database error during incremental sync: {e}", e)
        
        except Exception as e:
            self.logger.error(f"Unexpected error during incremental sync: {e}")
            raise DataSyncError(f"Unexpected error during incremental sync: {e}", e)
    
    def get_last_sync_date(self, repo_name: str) -> Optional[datetime]:
        """
        リポジトリの最終同期日を取得
        
        Args:
            repo_name: リポジトリ名
            
        Returns:
            最終同期日（存在しない場合はNone）
        """
        with self.db_manager.get_session() as session:
            sync_status = session.query(SyncStatus).filter_by(
                repo_name=repo_name
            ).first()
            
            if sync_status and sync_status.is_completed():
                return sync_status.last_synced_at
            return None
    
    def update_sync_status(self, repo_name: str, sync_result: Dict[str, Any]) -> None:
        """
        同期状態を更新
        
        Args:
            repo_name: リポジトリ名
            sync_result: 同期結果の辞書
        """
        with self.db_manager.get_session() as session:
            sync_status = session.query(SyncStatus).filter_by(
                repo_name=repo_name
            ).first()
            
            if not sync_status:
                sync_status = SyncStatus(repo_name=repo_name)
                session.add(sync_status)
            
            if sync_result.get('success', True):
                sync_status.status = 'completed'
                sync_status.last_synced_at = datetime.now(timezone.utc)
                if 'last_pr_number' in sync_result:
                    sync_status.last_pr_number = sync_result['last_pr_number']
            else:
                sync_status.status = 'error'
                sync_status.error_message = sync_result.get('error_message', 'Unknown error')
            
            session.commit()
    
    def _process_repositories_incremental(self, repositories: List[str]) -> Tuple[int, int, List[str]]:
        """
        差分同期用のリポジトリリスト処理
        
        各リポジトリに対して：
        1. 最終同期日を確認
        2. 差分データを取得
        3. データベースに保存
        4. 同期ステータスを更新
        
        Args:
            repositories: 処理対象のリポジトリリスト
            
        Returns:
            Tuple[取得したPR総数, 処理成功したリポジトリ数, 失敗したリポジトリリスト]
        """
        total_prs_fetched = 0
        processed_repositories = 0
        failed_repositories = []
        
        for repository in repositories:
            try:
                prs_count = self._process_single_repository_incremental(repository)
                total_prs_fetched += prs_count
                processed_repositories += 1
                
            except (GitHubAPIError, Exception) as e:
                error_message = f"Error during incremental sync for {repository}: {e}"
                self.logger.error(error_message)
                self.update_sync_status(repository, {'success': False, 'error_message': str(e)})
                failed_repositories.append(repository)
                # エラーが発生しても他のリポジトリの処理は継続
                continue
        
        return total_prs_fetched, processed_repositories, failed_repositories
    
    def _process_single_repository_incremental(self, repository: str) -> int:
        """
        単一リポジトリの差分同期を処理
        
        Args:
            repository: リポジトリ名
            
        Returns:
            取得したPR数
            
        Raises:
            ValueError: 初回同期が未実施の場合
            GitHubAPIError: GitHub API呼び出し時のエラー
        """
        # 最終同期日を取得
        last_sync_date = self.get_last_sync_date(repository)
        
        if last_sync_date is None:
            # 初回同期が未実施の場合はエラーとして扱う
            error_message = f"Repository {repository} has not been initially synced"
            self.logger.error(error_message)
            raise ValueError(error_message)
        
        # 差分データを取得
        pr_data = self.github_client.fetch_merged_prs(repo=repository, since=last_sync_date)
        
        if not pr_data:
            # 新しいデータなしでも成功として扱う
            self._update_sync_status_for_incremental(repository, [], success=True)
            return 0
        
        # データベースに保存
        saved_prs = self._save_pr_data(repository, pr_data)
        
        # 週次メトリクスを計算・保存
        if saved_prs:
            weekly_metrics = self.aggregator.calculate_weekly_metrics(pr_data)
            self._save_weekly_metrics(repository, weekly_metrics)
        
        # 同期ステータスを更新
        self._update_sync_status_for_incremental(repository, pr_data, success=True)
        
        return len(saved_prs)
    
    def _update_sync_status_for_incremental(self, repository: str, pr_data: List[Dict[str, Any]], 
                                          success: bool = True) -> None:
        """
        差分同期用の同期ステータス更新
        
        Args:
            repository: リポジトリ名
            pr_data: PRデータのリスト
            success: 同期が成功したかどうか
        """
        sync_result = {
            'pr_count': len(pr_data),
            'success': success
        }
        
        if pr_data and success:
            sync_result['last_pr_number'] = max(pr['number'] for pr in pr_data)
        
        self.update_sync_status(repository, sync_result)
    
    def fetch_period_data(self, repositories: List[str], from_date: str, to_date: str) -> Dict[str, Any]:
        """
        特定期間のデータを取得
        
        Args:
            repositories: 対象リポジトリのリスト
            from_date: 開始日（YYYY-MM-DD形式）
            to_date: 終了日（YYYY-MM-DD形式）
            
        Returns:
            取得結果を含む辞書
        """
        start_time = time.time()
        total_prs_fetched = 0
        
        try:
            # 日付をdatetimeオブジェクトに変換
            start_datetime = datetime.strptime(from_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_datetime = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            
            for repository in repositories:
                try:
                    # 期間指定でPRを取得（APIレベルでフィルタリング）
                    pr_data = self.github_client.fetch_merged_prs(
                        repo=repository, 
                        since=start_datetime, 
                        until=end_datetime
                    )
                    
                    if pr_data:
                        # データベースに保存
                        saved_prs = self._save_pr_data(repository, pr_data)
                        total_prs_fetched += len(saved_prs)
                        
                        # 週次メトリクスを計算・保存
                        weekly_metrics = self.aggregator.calculate_weekly_metrics(pr_data)
                        self._save_weekly_metrics(repository, weekly_metrics)
                        
                except Exception as e:
                    self.logger.error(f"Error fetching data for {repository}: {e}")
                    continue
            
            duration_seconds = time.time() - start_time
            
            return {
                'status': 'success',
                'fetched_prs': total_prs_fetched,
                'duration_seconds': duration_seconds
            }
            
        except Exception as e:
            self.logger.error(f"Error during period data fetch: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'duration_seconds': time.time() - start_time
            }