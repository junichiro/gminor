"""
初回データ取得機能を担当するモジュール
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
        
        if not repositories:
            return self._create_sync_result(0, 0, start_time)
        
        try:
            since_date = self._calculate_since_date(days_back)
            total_prs_fetched, processed_repositories = self._process_repositories(
                repositories, since_date, progress
            )
            
            if progress:
                self._display_completion_message(processed_repositories)
            
            return self._create_sync_result(processed_repositories, total_prs_fetched, start_time)
        
        except (DatabaseError, GitHubAPIError) as e:
            self.logger.error(f"Sync error: {e}")
            raise DataSyncError(f"Sync error: {e}", e)
        
        except Exception as e:
            self.logger.error(f"Unexpected error during sync: {e}")
            raise DataSyncError(f"Unexpected error during sync: {e}", e)
    
    def _calculate_since_date(self, days_back: int) -> datetime:
        """取得開始日を計算"""
        return datetime.now(timezone.utc) - timedelta(days=days_back)
    
    def _process_repositories(self, repositories: List[str], since_date: datetime, 
                            progress: bool) -> Tuple[int, int]:
        """
        リポジトリリストを処理
        
        Returns:
            Tuple[取得したPR総数, 処理したリポジトリ数]
        """
        total_prs_fetched = 0
        processed_repositories = 0
        
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
                raise DataSyncError(error_message, e)
        
        return total_prs_fetched, processed_repositories
    
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
                          start_time: float) -> Dict[str, Any]:
        """同期結果を作成"""
        return {
            'status': 'success',
            'processed_repositories': processed_repositories,
            'total_prs_fetched': total_prs_fetched,
            'sync_duration_seconds': time.time() - start_time
        }
    
    def _display_progress_message(self, current: int, total: int, repository: str) -> None:
        """プログレス表示メッセージを表示"""
        print(f"Processing repository {current}/{total}: {repository}")
    
    def _display_completion_message(self, processed_repositories: int) -> None:
        """完了メッセージを表示"""
        print(f"Completed synchronization of {processed_repositories} repositories")
    
    def _save_pr_data(self, repository: str, pr_data: List[Dict[str, Any]]) -> List[PullRequest]:
        """
        PRデータをデータベースに保存（重複チェック付き）
        
        Args:
            repository: リポジトリ名
            pr_data: PRデータのリスト
            
        Returns:
            保存されたPRオブジェクトのリスト
        """
        saved_prs = []
        
        with self.db_manager.get_session() as session:
            for pr_info in pr_data:
                # 重複チェック
                existing_pr = session.query(PullRequest).filter(
                    PullRequest.repo_name == repository,
                    PullRequest.pr_number == pr_info["number"]
                ).first()
                
                if not existing_pr:
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
            
            if saved_prs:
                session.add_all(saved_prs)
                session.commit()
        
        return saved_prs
    
    def _save_weekly_metrics(self, repository: str, weekly_metrics_df) -> None:
        """
        週次メトリクスをデータベースに保存
        
        Args:
            repository: リポジトリ名
            weekly_metrics_df: 週次メトリクスのDataFrame
        """
        if weekly_metrics_df.empty:
            return
        
        with self.db_manager.get_session() as session:
            for _, row in weekly_metrics_df.iterrows():
                # 重複チェック
                existing_metrics = session.query(WeeklyMetrics).filter(
                    WeeklyMetrics.repo_name == repository,
                    WeeklyMetrics.week_start_date == row['week_start'].date()
                ).first()
                
                if not existing_metrics:
                    metrics = WeeklyMetrics(
                        repo_name=repository,
                        week_start_date=row['week_start'].date(),
                        pr_count=row['pr_count'],
                        merged_pr_count=row['pr_count'],  # 集計済みデータはすべてマージ済み
                        total_authors=row['unique_authors']
                    )
                    session.add(metrics)
            
            session.commit()
    
    def _update_sync_status(self, repository: str, status: str, 
                          error_message: Optional[str] = None) -> None:
        """
        同期ステータスを更新
        
        Args:
            repository: リポジトリ名
            status: 同期ステータス
            error_message: エラーメッセージ（エラー時のみ）
        """
        with self.db_manager.get_session() as session:
            sync_status = session.query(SyncStatus).filter_by(
                repo_name=repository
            ).first()
            
            if not sync_status:
                sync_status = SyncStatus(repo_name=repository)
                session.add(sync_status)
            
            sync_status.status = status
            sync_status.last_synced_at = datetime.now(timezone.utc)
            if error_message:
                sync_status.error_message = error_message
            
            session.commit()