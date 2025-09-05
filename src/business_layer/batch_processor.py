"""バッチ処理最適化モジュール - 大量データの効率的な処理"""
import logging
from typing import List, Dict, Any, Iterator, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """バッチ処理設定"""
    batch_size: int = 100
    max_memory_mb: int = 50
    enable_parallel: bool = True


class BatchProcessor:
    """大量データの効率的なバッチ処理クラス"""
    
    def __init__(self, batch_size: int = 100, max_memory_mb: int = 50):
        """
        BatchProcessorを初期化
        
        Args:
            batch_size: バッチサイズ（デフォルト: 100）
            max_memory_mb: 最大メモリ使用量（MB）（デフォルト: 50MB）
        """
        self.config = BatchConfig(
            batch_size=batch_size,
            max_memory_mb=max_memory_mb
        )
        logger.info(f"BatchProcessor initialized with batch_size={batch_size}, max_memory_mb={max_memory_mb}")
    
    def process_prs_in_batches(self, prs: List[Dict[str, Any]], batch_size: int = None) -> Iterator[List[Dict[str, Any]]]:
        """
        PRデータをバッチ単位で処理
        
        Args:
            prs: PRデータのリスト
            batch_size: バッチサイズ（Noneの場合は設定値を使用）
            
        Yields:
            Iterator[List[Dict[str, Any]]]: バッチ単位のPRデータ
        """
        if batch_size is None:
            batch_size = self.config.batch_size
        
        logger.debug(f"Processing {len(prs)} PRs in batches of {batch_size}")
        
        for i in range(0, len(prs), batch_size):
            batch = prs[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}, size: {len(batch)}")
            yield batch
    
    def get_batch_size(self) -> int:
        """現在のバッチサイズを取得"""
        return self.config.batch_size
    
    def get_max_memory_mb(self) -> int:
        """最大メモリ使用量を取得"""
        return self.config.max_memory_mb
    
    def estimate_memory_usage(self, data_count: int, avg_record_size_kb: float = 1.0) -> float:
        """
        メモリ使用量を推定
        
        Args:
            data_count: データ件数
            avg_record_size_kb: 1レコードあたりの平均サイズ（KB）
            
        Returns:
            float: 推定メモリ使用量（MB）
        """
        estimated_mb = (data_count * avg_record_size_kb) / 1024
        logger.debug(f"Estimated memory usage: {estimated_mb:.2f}MB for {data_count} records")
        return estimated_mb
    
    def optimize_batch_size_for_memory(self, total_records: int, avg_record_size_kb: float = 1.0) -> int:
        """
        メモリ制限に基づいて最適なバッチサイズを計算
        
        Args:
            total_records: 総レコード数
            avg_record_size_kb: 1レコードあたりの平均サイズ（KB）
            
        Returns:
            int: 最適なバッチサイズ
        """
        max_memory_kb = self.config.max_memory_mb * 1024
        optimal_batch_size = int(max_memory_kb / avg_record_size_kb)
        
        # 最小バッチサイズを10、最大を元の設定値に制限
        optimal_batch_size = max(10, min(optimal_batch_size, self.config.batch_size))
        
        logger.info(f"Optimized batch size: {optimal_batch_size} for {total_records} records")
        return optimal_batch_size