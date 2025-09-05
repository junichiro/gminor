"""パフォーマンス統合レイヤー - 既存コンポーネントとの性能最適化統合"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .sync_manager import SyncManager
from .performance_optimizer import PerformanceOptimizer, PerformanceConfig
from .batch_processor import BatchProcessor

logger = logging.getLogger(__name__)


class PerformanceEnhancedSyncManager:
    """パフォーマンス強化版SyncManager"""
    
    def __init__(self, sync_manager: SyncManager, 
                 performance_config: Optional[PerformanceConfig] = None):
        """
        PerformanceEnhancedSyncManagerを初期化
        
        Args:
            sync_manager: 既存のSyncManager
            performance_config: パフォーマンス設定
        """
        self.sync_manager = sync_manager
        self.performance_optimizer = PerformanceOptimizer(performance_config)
        self.batch_processor = BatchProcessor(
            batch_size=performance_config.batch_size if performance_config else 100
        )
        logger.info("PerformanceEnhancedSyncManager initialized")
    
    def optimized_initial_sync(self, repositories: List[str], days_back: int = 180, 
                              progress: bool = False) -> Dict[str, Any]:
        """
        パフォーマンス最適化された初回同期
        
        Args:
            repositories: 同期対象のリポジトリリスト
            days_back: 過去何日分のデータを取得するか
            progress: プログレス表示するかどうか
            
        Returns:
            Dict[str, Any]: 最適化された同期結果
        """
        logger.info(f"Starting optimized initial sync for {len(repositories)} repositories")
        
        # リポジトリ数に応じた最適化戦略を選択
        if len(repositories) > 5 and self.performance_optimizer.config.enable_parallel:
            return self._parallel_repository_sync(repositories, days_back, progress)
        else:
            return self._batched_repository_sync(repositories, days_back, progress)
    
    def _parallel_repository_sync(self, repositories: List[str], days_back: int, 
                                 progress: bool) -> Dict[str, Any]:
        """
        並列リポジトリ同期を実行
        
        Args:
            repositories: リポジトリリスト
            days_back: 日数
            progress: プログレス表示
            
        Returns:
            Dict[str, Any]: 同期結果
        """
        from .parallel_sync_manager import ParallelSyncManager
        
        logger.info(f"Executing parallel repository sync for {len(repositories)} repositories")
        
        try:
            parallel_manager = ParallelSyncManager(
                max_workers=self.performance_optimizer.config.max_workers
            )
            
            result = parallel_manager.parallel_initial_sync(
                self.sync_manager, repositories, days_back, progress
            )
            
            # パフォーマンス統計を追加
            performance_stats = {
                'optimization_method': 'parallel_sync',
                'parallel_efficiency': result.parallel_efficiency,
                'workers_used': parallel_manager.get_max_workers(),
                'repositories_per_worker': len(repositories) / parallel_manager.get_max_workers()
            }
            
            return {
                'status': result.status,
                'processed_repositories': result.successful_repositories,
                'total_prs_fetched': result.total_prs_fetched,
                'sync_duration_seconds': result.sync_duration_seconds,
                'failed_repositories': result.failed_repositories,
                'performance_stats': performance_stats,
                'optimization_applied': True
            }
            
        except Exception as e:
            logger.error(f"Parallel sync failed, falling back to sequential: {e}")
            return self.sync_manager.initial_sync(repositories, days_back, progress)
    
    def _batched_repository_sync(self, repositories: List[str], days_back: int, 
                               progress: bool) -> Dict[str, Any]:
        """
        バッチリポジトリ同期を実行
        
        Args:
            repositories: リポジトリリスト
            days_back: 日数
            progress: プログレス表示
            
        Returns:
            Dict[str, Any]: 同期結果
        """
        logger.info(f"Executing batched repository sync for {len(repositories)} repositories")
        
        # リポジトリをバッチに分割
        batch_size = min(self.batch_processor.get_batch_size(), len(repositories))
        batches = list(self.batch_processor.process_prs_in_batches(
            [{'repo': repo} for repo in repositories], 
            batch_size
        ))
        
        total_prs_fetched = 0
        processed_repositories = 0
        failed_repositories = []
        batch_results = []
        
        for i, batch in enumerate(batches):
            batch_repos = [item['repo'] for item in batch]
            logger.debug(f"Processing batch {i+1}/{len(batches)}: {len(batch_repos)} repositories")
            
            try:
                batch_result = self.sync_manager.initial_sync(batch_repos, days_back, False)
                
                total_prs_fetched += batch_result['total_prs_fetched']
                processed_repositories += batch_result['processed_repositories']
                
                if 'failed_repositories' in batch_result:
                    failed_repositories.extend(batch_result['failed_repositories'])
                
                batch_results.append({
                    'batch_id': i,
                    'batch_size': len(batch_repos),
                    'result': batch_result
                })
                
            except Exception as e:
                logger.error(f"Batch {i+1} failed: {e}")
                failed_repositories.extend(batch_repos)
        
        status = 'success' if not failed_repositories else 'partial_success'
        
        return {
            'status': status,
            'processed_repositories': processed_repositories,
            'total_prs_fetched': total_prs_fetched,
            'failed_repositories': failed_repositories,
            'batches_processed': len(batches),
            'batch_results': batch_results,
            'performance_stats': {
                'optimization_method': 'batched_sync',
                'batch_size': batch_size,
                'batches_count': len(batches)
            },
            'optimization_applied': True
        }
    
    def optimized_pr_data_processing(self, pr_data_list: List[Dict[str, Any]], 
                                   repository: str) -> Dict[str, Any]:
        """
        パフォーマンス最適化されたPRデータ処理
        
        Args:
            pr_data_list: PRデータのリスト
            repository: リポジトリ名
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        logger.info(f"Starting optimized PR data processing: {len(pr_data_list)} PRs for {repository}")
        
        # データサイズに応じて最適化を適用
        if len(pr_data_list) > 1000:
            return self.performance_optimizer.optimize_data_processing(
                pr_data_list, 
                f"pr_processing_{repository}"
            )
        else:
            # 小さなデータセットは通常処理
            return {
                'status': 'success',
                'processed_data': pr_data_list,
                'optimization_applied': False,
                'processing_method': 'standard'
            }
    
    def get_optimization_recommendations(self, repositories: List[str], 
                                       estimated_pr_count: int) -> Dict[str, Any]:
        """
        パフォーマンス最適化の推奨設定を取得
        
        Args:
            repositories: リポジトリリスト
            estimated_pr_count: 推定PR数
            
        Returns:
            Dict[str, Any]: 最適化推奨設定
        """
        recommendations = {
            'repository_count': len(repositories),
            'estimated_pr_count': estimated_pr_count,
            'recommendations': []
        }
        
        # 並列処理の推奨
        if len(repositories) > 3:
            optimal_workers = min(len(repositories), 8)
            recommendations['recommendations'].append({
                'optimization': 'parallel_processing',
                'recommended_workers': optimal_workers,
                'expected_speedup': f"{min(optimal_workers, len(repositories)):.1f}x",
                'condition': 'Multiple repositories detected'
            })
        
        # バッチ処理の推奨
        if estimated_pr_count > 1000:
            recommended_batch_size = min(500, estimated_pr_count // 10)
            recommendations['recommendations'].append({
                'optimization': 'batch_processing',
                'recommended_batch_size': recommended_batch_size,
                'expected_memory_saving': '60-80%',
                'condition': 'Large dataset detected'
            })
        
        # キャッシュの推奨
        if estimated_pr_count > 100:
            recommendations['recommendations'].append({
                'optimization': 'caching',
                'cache_ttl_hours': 1,
                'expected_speedup': '2-5x for repeated queries',
                'condition': 'Frequent data access expected'
            })
        
        # チャンク処理の推奨
        if estimated_pr_count > 5000:
            recommendations['recommendations'].append({
                'optimization': 'chunked_processing',
                'recommended_chunk_size': 1000,
                'memory_limit_mb': 100,
                'condition': 'Very large dataset detected'
            })
        
        return recommendations
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        パフォーマンスレポートを取得
        
        Returns:
            Dict[str, Any]: パフォーマンスレポート
        """
        summary = self.performance_optimizer.get_performance_summary()
        
        return {
            'performance_summary': summary,
            'batch_processor_config': {
                'batch_size': self.batch_processor.get_batch_size(),
                'max_memory_mb': self.batch_processor.get_max_memory_mb()
            },
            'optimization_history': [
                m.to_dict() for m in self.performance_optimizer.metrics_history
            ],
            'total_optimized_operations': len(self.performance_optimizer.metrics_history)
        }