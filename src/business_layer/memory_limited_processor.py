"""メモリ制限付きプロセッサー - メモリ使用量を制限した大量データ処理"""
import logging
import time
import gc
from typing import Dict, Any
import psutil
import os

logger = logging.getLogger(__name__)


class MemoryLimitedProcessor:
    """メモリ使用量を制限した大量データ処理クラス"""
    
    def __init__(self, memory_limit_mb: int = 100):
        """
        MemoryLimitedProcessorを初期化
        
        Args:
            memory_limit_mb: メモリ制限（MB）
        """
        self.memory_limit_mb = memory_limit_mb
        self.process = psutil.Process(os.getpid())
        logger.info(f"MemoryLimitedProcessor initialized with memory limit: {memory_limit_mb}MB")
    
    def process_large_dataset(self) -> Dict[str, Any]:
        """
        メモリ制限付きで大量データセットを処理
        
        Returns:
            Dict[str, Any]: 処理結果
        """
        start_time = time.time()
        initial_memory_mb = self.process.memory_info().rss / 1024 / 1024
        peak_memory_mb = initial_memory_mb
        
        logger.info(f"Starting memory-limited processing (limit: {self.memory_limit_mb}MB)")
        
        try:
            processed_batches = 0
            total_items_processed = 0
            
            # シミュレートされた大量データ処理
            for batch_idx in range(10):  # 10バッチの処理をシミュレート
                # メモリ使用量をチェック
                current_memory_mb = self.process.memory_info().rss / 1024 / 1024
                memory_used_mb = current_memory_mb - initial_memory_mb
                peak_memory_mb = max(peak_memory_mb, current_memory_mb)
                
                # メモリ制限チェック
                if memory_used_mb > self.memory_limit_mb:
                    logger.warning(f"Memory limit exceeded: {memory_used_mb:.2f}MB > {self.memory_limit_mb}MB")
                    # ガベージコレクションを実行
                    gc.collect()
                    
                    # メモリ使用量を再チェック
                    current_memory_mb = self.process.memory_info().rss / 1024 / 1024
                    memory_used_mb = current_memory_mb - initial_memory_mb
                    
                    if memory_used_mb > self.memory_limit_mb:
                        logger.error(f"Memory limit still exceeded after GC: {memory_used_mb:.2f}MB")
                        return {
                            'status': 'error',
                            'error': f'Memory limit exceeded: {memory_used_mb:.2f}MB > {self.memory_limit_mb}MB',
                            'peak_memory_mb': peak_memory_mb - initial_memory_mb,
                            'processed_batches': processed_batches
                        }
                
                # バッチ処理をシミュレート
                batch_result = self._process_batch(batch_idx)
                total_items_processed += batch_result['items_processed']
                processed_batches += 1
                
                logger.debug(f"Batch {batch_idx + 1} processed: {batch_result['items_processed']} items, "
                           f"memory: {memory_used_mb:.2f}MB")
            
            end_time = time.time()
            processing_time = end_time - start_time
            final_peak_memory_mb = peak_memory_mb - initial_memory_mb
            
            result = {
                'status': 'success',
                'processed_batches': processed_batches,
                'total_items_processed': total_items_processed,
                'processing_time_seconds': processing_time,
                'peak_memory_mb': final_peak_memory_mb,
                'memory_limit_mb': self.memory_limit_mb,
                'memory_efficiency': (total_items_processed / final_peak_memory_mb) if final_peak_memory_mb > 0 else 0
            }
            
            logger.info(f"Memory-limited processing completed: {processed_batches} batches, "
                       f"{total_items_processed} items, peak memory: {final_peak_memory_mb:.2f}MB")
            
            return result
            
        except Exception as e:
            logger.error(f"Memory-limited processing failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'peak_memory_mb': peak_memory_mb - initial_memory_mb
            }
    
    def _process_batch(self, batch_idx: int) -> Dict[str, Any]:
        """
        単一バッチの処理をシミュレート
        
        Args:
            batch_idx: バッチインデックス
            
        Returns:
            Dict[str, Any]: バッチ処理結果
        """
        # バッチ処理をシミュレート（実際の処理では大量データの計算を行う）
        items_processed = 1000 + (batch_idx * 100)  # 各バッチで異なる数のアイテムを処理
        
        # 少しの計算負荷をシミュレート
        dummy_data = list(range(items_processed))
        processed_sum = sum(dummy_data)
        
        # メモリリークを防ぐため明示的に削除
        del dummy_data
        
        return {
            'batch_idx': batch_idx,
            'items_processed': items_processed,
            'processing_result': processed_sum
        }
    
    def get_current_memory_usage(self) -> Dict[str, float]:
        """
        現在のメモリ使用量を取得
        
        Returns:
            Dict[str, float]: メモリ使用量情報
        """
        memory_info = self.process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # 物理メモリ使用量
            'vms_mb': memory_info.vms / 1024 / 1024,  # 仮想メモリ使用量
            'memory_limit_mb': self.memory_limit_mb,
            'memory_available_mb': self.memory_limit_mb - (memory_info.rss / 1024 / 1024)
        }