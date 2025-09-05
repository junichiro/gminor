"""並列同期処理マネージャー - 複数リポジトリの並列処理"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .sync_manager import SyncManager, DataSyncError

logger = logging.getLogger(__name__)


@dataclass
class ParallelSyncResult:
    """並列同期処理結果"""
    status: str
    total_repositories: int
    successful_repositories: int
    failed_repositories: List[str]
    total_prs_fetched: int
    sync_duration_seconds: float
    parallel_efficiency: float  # 並列処理効率 (実処理時間 / 並列実行時間)


class ParallelSyncManager:
    """複数リポジトリの並列同期処理クラス"""
    
    def __init__(self, max_workers: int = 4):
        """
        ParallelSyncManagerを初期化
        
        Args:
            max_workers: 最大ワーカー数（デフォルト: 4）
        """
        self.max_workers = max_workers
        logger.info(f"ParallelSyncManager initialized with max_workers={max_workers}")
    
    def parallel_initial_sync(self, sync_manager: SyncManager, repositories: List[str], 
                            days_back: int = 180, progress: bool = False) -> ParallelSyncResult:
        """
        複数リポジトリの並列初回同期
        
        Args:
            sync_manager: SyncManagerインスタンス
            repositories: 同期対象のリポジトリリスト
            days_back: 過去何日分のデータを取得するか
            progress: プログレス表示するかどうか
            
        Returns:
            ParallelSyncResult: 並列同期処理結果
            
        Raises:
            DataSyncError: 並列同期処理でエラーが発生した場合
        """
        start_time = time.time()
        
        logger.info(f"Starting parallel sync for {len(repositories)} repositories with {self.max_workers} workers")
        
        if not repositories:
            return ParallelSyncResult(
                status='success',
                total_repositories=0,
                successful_repositories=0,
                failed_repositories=[],
                total_prs_fetched=0,
                sync_duration_seconds=0.0,
                parallel_efficiency=1.0
            )
        
        successful_repositories = 0
        failed_repositories = []
        total_prs_fetched = 0
        individual_durations = []
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 各リポジトリの同期タスクを作成
                future_to_repo = {
                    executor.submit(
                        self._sync_single_repository, 
                        sync_manager, repo, days_back, progress
                    ): repo
                    for repo in repositories
                }
                
                # 並列実行結果を収集
                for future in as_completed(future_to_repo):
                    repo = future_to_repo[future]
                    try:
                        result = future.result()
                        if result['status'] == 'success':
                            successful_repositories += 1
                            total_prs_fetched += result['total_prs_fetched']
                            individual_durations.append(result['sync_duration_seconds'])
                            logger.info(f"✅ Repository {repo} synced successfully: {result['total_prs_fetched']} PRs")
                        else:
                            failed_repositories.append(repo)
                            logger.warning(f"❌ Repository {repo} sync failed: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        failed_repositories.append(repo)
                        logger.error(f"❌ Repository {repo} sync failed with exception: {e}")
            
            end_time = time.time()
            parallel_duration = end_time - start_time
            
            # 並列処理効率を計算（理想的なシーケンシャル実行時間 / 実際の並列実行時間）
            sequential_duration = sum(individual_durations) if individual_durations else 0
            parallel_efficiency = sequential_duration / parallel_duration if parallel_duration > 0 else 1.0
            
            status = 'success' if not failed_repositories else 'partial_success'
            
            result = ParallelSyncResult(
                status=status,
                total_repositories=len(repositories),
                successful_repositories=successful_repositories,
                failed_repositories=failed_repositories,
                total_prs_fetched=total_prs_fetched,
                sync_duration_seconds=parallel_duration,
                parallel_efficiency=parallel_efficiency
            )
            
            logger.info(f"Parallel sync completed: {successful_repositories}/{len(repositories)} successful, "
                       f"{total_prs_fetched} PRs fetched in {parallel_duration:.2f}s "
                       f"(efficiency: {parallel_efficiency:.1f}x)")
            
            return result
        
        except Exception as e:
            logger.error(f"Parallel sync failed: {e}")
            raise DataSyncError(f"Parallel sync failed: {e}", e)
    
    def _sync_single_repository(self, sync_manager: SyncManager, repository: str, 
                              days_back: int, progress: bool) -> Dict[str, Any]:
        """
        単一リポジトリの同期処理（並列実行用）
        
        Args:
            sync_manager: SyncManagerインスタンス
            repository: リポジトリ名
            days_back: 過去何日分のデータを取得するか
            progress: プログレス表示するかどうか
            
        Returns:
            Dict[str, Any]: 同期結果
        """
        try:
            # 単一リポジトリの同期を実行
            result = sync_manager.initial_sync([repository], days_back, progress=False)
            return result
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'total_prs_fetched': 0,
                'sync_duration_seconds': 0.0
            }
    
    def get_max_workers(self) -> int:
        """最大ワーカー数を取得"""
        return self.max_workers
    
    def estimate_optimal_workers(self, repository_count: int) -> int:
        """
        リポジトリ数に基づいて最適なワーカー数を推定
        
        Args:
            repository_count: リポジトリ数
            
        Returns:
            int: 推奨ワーカー数
        """
        # リポジトリ数が少ない場合はワーカー数を制限
        optimal_workers = min(self.max_workers, repository_count, 8)  # 最大8ワーカー
        logger.debug(f"Optimal workers for {repository_count} repositories: {optimal_workers}")
        return optimal_workers