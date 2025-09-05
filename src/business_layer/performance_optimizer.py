"""統合パフォーマンス最適化モジュール - 大量データ処理の包括的な性能向上"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """パフォーマンス最適化設定"""
    # バッチ処理設定
    batch_size: int = 100
    max_memory_mb: int = 50
    
    # 並列処理設定
    enable_parallel: bool = True
    max_workers: int = 4
    
    # キャッシュ設定
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    
    # データベース最適化設定
    enable_pagination: bool = True
    page_size: int = 100
    enable_bulk_operations: bool = True
    
    # その他設定
    enable_chunked_processing: bool = True
    chunk_size: int = 500


@dataclass
class PerformanceMetrics:
    """パフォーマンス測定結果"""
    operation_name: str
    start_time: float
    end_time: float
    processing_time_seconds: float
    records_processed: int
    memory_peak_mb: float
    throughput_per_second: float
    optimization_flags: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'operation_name': self.operation_name,
            'processing_time_seconds': self.processing_time_seconds,
            'records_processed': self.records_processed,
            'memory_peak_mb': self.memory_peak_mb,
            'throughput_per_second': self.throughput_per_second,
            'optimization_flags': self.optimization_flags
        }


class PerformanceOptimizer:
    """統合パフォーマンス最適化クラス"""
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        """
        PerformanceOptimizerを初期化
        
        Args:
            config: パフォーマンス設定（Noneの場合はデフォルト設定を使用）
        """
        self.config = config if config else PerformanceConfig()
        self.metrics_history: List[PerformanceMetrics] = []
        logger.info(f"PerformanceOptimizer initialized with config: {self.config}")
    
    def optimize_data_processing(self, data: List[Dict[str, Any]], 
                                operation_name: str = "data_processing") -> Dict[str, Any]:
        """
        データ処理の最適化実行
        
        Args:
            data: 処理対象データ
            operation_name: オペレーション名
            
        Returns:
            Dict[str, Any]: 最適化された処理結果
        """
        start_time = time.time()
        logger.info(f"Starting optimized data processing: {operation_name} ({len(data)} records)")
        
        try:
            # 最適化戦略の選択
            optimization_strategy = self._select_optimization_strategy(len(data))
            logger.info(f"Selected optimization strategy: {optimization_strategy}")
            
            # データ処理実行
            if optimization_strategy == "chunked_parallel":
                result = self._process_chunked_parallel(data)
            elif optimization_strategy == "batch_processing":
                result = self._process_in_batches(data)
            elif optimization_strategy == "simple_processing":
                result = self._process_simple(data)
            else:
                raise ValueError(f"Unknown optimization strategy: {optimization_strategy}")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # パフォーマンスメトリクスを記録
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                processing_time_seconds=processing_time,
                records_processed=len(data),
                memory_peak_mb=result.get('memory_peak_mb', 0),
                throughput_per_second=len(data) / processing_time if processing_time > 0 else 0,
                optimization_flags={
                    'strategy': optimization_strategy,
                    'chunked_processing': optimization_strategy in ["chunked_parallel", "batch_processing"],
                    'parallel_processing': optimization_strategy == "chunked_parallel"
                }
            )
            
            self.metrics_history.append(metrics)
            
            # 結果に最適化情報を追加
            result.update({
                'performance_metrics': metrics.to_dict(),
                'optimization_applied': True,
                'strategy_used': optimization_strategy
            })
            
            logger.info(f"Optimized processing completed: {optimization_strategy} in {processing_time:.2f}s, "
                       f"throughput: {metrics.throughput_per_second:.1f} records/s")
            
            return result
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'optimization_applied': False,
                'processing_time_seconds': time.time() - start_time
            }
    
    def _select_optimization_strategy(self, data_count: int) -> str:
        """
        データサイズに基づいて最適化戦略を選択
        
        Args:
            data_count: データ件数
            
        Returns:
            str: 選択された戦略名
        """
        if data_count >= 10000 and self.config.enable_parallel and self.config.enable_chunked_processing:
            return "chunked_parallel"
        elif data_count >= 1000 and self.config.enable_chunked_processing:
            return "batch_processing"
        else:
            return "simple_processing"
    
    def _process_chunked_parallel(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        チャンク並列処理を実行
        
        Args:
            data: 処理対象データ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        logger.debug(f"Executing chunked parallel processing with {self.config.max_workers} workers")
        
        chunks = self._create_chunks(data, self.config.chunk_size)
        processed_results = []
        memory_peak_mb = 0
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 各チャンクを並列処理
            futures = [executor.submit(self._process_chunk, chunk, i) for i, chunk in enumerate(chunks)]
            
            for future in futures:
                chunk_result = future.result()
                processed_results.extend(chunk_result['processed_data'])
                memory_peak_mb = max(memory_peak_mb, chunk_result.get('memory_used_mb', 0))
        
        return {
            'status': 'success',
            'processed_data': processed_results,
            'chunks_processed': len(chunks),
            'memory_peak_mb': memory_peak_mb,
            'parallel_workers_used': self.config.max_workers
        }
    
    def _process_in_batches(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        バッチ処理を実行
        
        Args:
            data: 処理対象データ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        logger.debug(f"Executing batch processing with batch size {self.config.batch_size}")
        
        batches = self._create_chunks(data, self.config.batch_size)
        processed_results = []
        memory_peak_mb = 0
        
        for i, batch in enumerate(batches):
            batch_result = self._process_chunk(batch, i)
            processed_results.extend(batch_result['processed_data'])
            memory_peak_mb = max(memory_peak_mb, batch_result.get('memory_used_mb', 0))
        
        return {
            'status': 'success',
            'processed_data': processed_results,
            'batches_processed': len(batches),
            'memory_peak_mb': memory_peak_mb
        }
    
    def _process_simple(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        シンプル処理を実行
        
        Args:
            data: 処理対象データ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        logger.debug("Executing simple processing")
        
        # シンプルなデータ処理（実際の処理は具体的な用途に応じて実装）
        processed_data = []
        for item in data:
            # 基本的な処理（例：データ検証、変換など）
            processed_item = {
                **item,
                'processed_at': time.time(),
                'processing_method': 'simple'
            }
            processed_data.append(processed_item)
        
        return {
            'status': 'success',
            'processed_data': processed_data,
            'memory_peak_mb': 5.0  # 推定値
        }
    
    def _create_chunks(self, data: List[Dict[str, Any]], chunk_size: int) -> List[List[Dict[str, Any]]]:
        """
        データをチャンクに分割
        
        Args:
            data: 分割対象データ
            chunk_size: チャンクサイズ
            
        Returns:
            List[List[Dict[str, Any]]]: チャンクのリスト
        """
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def _process_chunk(self, chunk: List[Dict[str, Any]], chunk_id: int) -> Dict[str, Any]:
        """
        単一チャンクの処理
        
        Args:
            chunk: チャンクデータ
            chunk_id: チャンクID
            
        Returns:
            Dict[str, Any]: チャンク処理結果
        """
        logger.debug(f"Processing chunk {chunk_id} with {len(chunk)} items")
        
        processed_chunk = []
        for item in chunk:
            # チャンク処理（具体的な処理は用途に応じて実装）
            processed_item = {
                **item,
                'chunk_id': chunk_id,
                'processed_at': time.time(),
                'processing_method': 'chunked'
            }
            processed_chunk.append(processed_item)
        
        return {
            'processed_data': processed_chunk,
            'chunk_id': chunk_id,
            'items_processed': len(chunk),
            'memory_used_mb': len(chunk) * 0.001  # 推定メモリ使用量（1KB/item）
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        パフォーマンスサマリーを取得
        
        Returns:
            Dict[str, Any]: パフォーマンスサマリー
        """
        if not self.metrics_history:
            return {
                'total_operations': 0,
                'average_throughput': 0,
                'total_records_processed': 0
            }
        
        total_operations = len(self.metrics_history)
        total_records = sum(m.records_processed for m in self.metrics_history)
        total_time = sum(m.processing_time_seconds for m in self.metrics_history)
        average_throughput = total_records / total_time if total_time > 0 else 0
        
        # 最適化戦略の使用統計
        strategies_used = {}
        for metrics in self.metrics_history:
            strategy = metrics.optimization_flags.get('strategy', 'unknown')
            strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
        
        return {
            'total_operations': total_operations,
            'total_records_processed': total_records,
            'total_processing_time_seconds': total_time,
            'average_throughput_per_second': average_throughput,
            'strategies_used': strategies_used,
            'config': {
                'batch_size': self.config.batch_size,
                'max_workers': self.config.max_workers,
                'chunk_size': self.config.chunk_size,
                'optimizations_enabled': {
                    'parallel': self.config.enable_parallel,
                    'chunked': self.config.enable_chunked_processing,
                    'cache': self.config.enable_cache,
                    'pagination': self.config.enable_pagination
                }
            }
        }
    
    def export_metrics_report(self) -> str:
        """
        メトリクスレポートをJSON形式でエクスポート
        
        Returns:
            str: JSON形式のレポート
        """
        report = {
            'summary': self.get_performance_summary(),
            'detailed_metrics': [m.to_dict() for m in self.metrics_history],
            'generated_at': time.time()
        }
        
        return json.dumps(report, indent=2, default=str)