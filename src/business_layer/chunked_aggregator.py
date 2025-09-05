"""チャンク処理による大量データ集計 - メモリ効率的な集計処理"""
import logging
import time
from typing import List, Dict, Any, Iterator
import pandas as pd
import psutil
import os

logger = logging.getLogger(__name__)


class ChunkedAggregator:
    """大量データのチャンク処理による効率的な集計クラス"""
    
    def __init__(self, chunk_size: int = 500):
        """
        ChunkedAggregatorを初期化
        
        Args:
            chunk_size: チャンクサイズ（デフォルト: 500）
        """
        self.chunk_size = chunk_size
        logger.info(f"ChunkedAggregator initialized with chunk_size={chunk_size}")
    
    def calculate_weekly_metrics_chunked(self, total_records: int) -> Dict[str, Any]:
        """
        チャンク処理で週次メトリクスを計算
        
        Args:
            total_records: 処理対象の総レコード数
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        start_time = time.time()
        
        logger.info(f"Starting chunked aggregation for {total_records} records")
        
        chunks_processed = 0
        total_metrics = []
        peak_memory_mb = 0
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            # チャンク単位で処理
            for chunk_start in range(0, total_records, self.chunk_size):
                chunk_end = min(chunk_start + self.chunk_size, total_records)
                chunk_data = self._generate_chunk_data(chunk_start, chunk_end)
                
                # チャンクデータの集計
                chunk_metrics = self._aggregate_chunk(chunk_data)
                total_metrics.append(chunk_metrics)
                
                chunks_processed += 1
                
                # メモリ使用量を監視
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_used = current_memory - initial_memory
                peak_memory_mb = max(peak_memory_mb, memory_used)
                
                logger.debug(f"Processed chunk {chunks_processed}: records {chunk_start}-{chunk_end-1}, "
                           f"memory: {memory_used:.2f}MB")
            
            # 全チャンクの結果をマージ
            final_metrics = self._merge_chunk_results(total_metrics)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            result = {
                'status': 'success',
                'chunks_processed': chunks_processed,
                'total_records_processed': total_records,
                'processing_time_seconds': processing_time,
                'memory_peak_mb': peak_memory_mb,
                'final_metrics_count': len(final_metrics) if final_metrics is not None else 0
            }
            
            logger.info(f"Chunked aggregation completed: {chunks_processed} chunks, "
                       f"{processing_time:.2f}s, peak memory: {peak_memory_mb:.2f}MB")
            
            return result
            
        except Exception as e:
            logger.error(f"Chunked aggregation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'chunks_processed': chunks_processed,
                'memory_peak_mb': peak_memory_mb
            }
    
    def _generate_chunk_data(self, start_idx: int, end_idx: int) -> pd.DataFrame:
        """
        チャンクデータを生成（テスト用）
        
        Args:
            start_idx: 開始インデックス
            end_idx: 終了インデックス
            
        Returns:
            pd.DataFrame: チャンクデータ
        """
        chunk_size = end_idx - start_idx
        
        # テスト用のサンプルデータを生成
        data = {
            'id': list(range(start_idx, end_idx)),
            'author': [f'user_{i % 50}' for i in range(start_idx, end_idx)],
            'week': [f'2024-W{(i % 52) + 1:02d}' for i in range(start_idx, end_idx)],
            'pr_count': [1] * chunk_size  # 各レコードは1PR
        }
        
        return pd.DataFrame(data)
    
    def _aggregate_chunk(self, chunk_data: pd.DataFrame) -> Dict[str, Any]:
        """
        チャンクデータを集計
        
        Args:
            chunk_data: チャンクデータ
            
        Returns:
            Dict[str, Any]: 集計結果
        """
        # 週次集計
        weekly_agg = chunk_data.groupby('week').agg({
            'pr_count': 'sum',
            'author': 'nunique'
        }).rename(columns={'author': 'unique_authors'})
        
        return {
            'weekly_metrics': weekly_agg.to_dict('index'),
            'chunk_size': len(chunk_data),
            'unique_authors_total': chunk_data['author'].nunique()
        }
    
    def _merge_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        チャンク結果をマージ
        
        Args:
            chunk_results: チャンク結果のリスト
            
        Returns:
            Dict[str, Any]: マージされた結果
        """
        if not chunk_results:
            return None
        
        # 全週次メトリクスをマージ
        merged_weekly = {}
        total_unique_authors = set()
        
        for chunk_result in chunk_results:
            weekly_metrics = chunk_result['weekly_metrics']
            
            for week, metrics in weekly_metrics.items():
                if week not in merged_weekly:
                    merged_weekly[week] = {
                        'pr_count': 0,
                        'unique_authors': 0
                    }
                
                merged_weekly[week]['pr_count'] += metrics['pr_count']
                # unique_authorsは後で再計算が必要（チャンク単位では正確でない）
        
        return {
            'weekly_metrics': merged_weekly,
            'total_weeks': len(merged_weekly)
        }