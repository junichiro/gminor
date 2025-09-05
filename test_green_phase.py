#!/usr/bin/env python3
"""GREENフェーズテスト実行器 - 最小実装の動作確認"""
import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_batch_processor():
    """BatchProcessor実装テスト"""
    print("=== BatchProcessor実装テスト ===")
    
    try:
        from src.business_layer.batch_processor import BatchProcessor
        
        # BatchProcessorを初期化
        batch_processor = BatchProcessor(batch_size=50)
        
        # 設定値の確認
        assert batch_processor.get_batch_size() == 50
        assert batch_processor.get_max_memory_mb() == 50
        
        # バッチ処理のテスト
        test_data = [{'id': i, 'data': f'test{i}'} for i in range(100)]
        batches = list(batch_processor.process_prs_in_batches(test_data, batch_size=25))
        
        assert len(batches) == 4  # 100個のデータを25個ずつ = 4バッチ
        assert len(batches[0]) == 25
        assert len(batches[-1]) == 25
        
        print("✅ BatchProcessor実装成功 - 基本機能が動作")
        return True
        
    except Exception as e:
        print(f"❌ BatchProcessor実装エラー: {e}")
        return False

def test_parallel_sync_manager():
    """ParallelSyncManager実装テスト"""
    print("\n=== ParallelSyncManager実装テスト ===")
    
    try:
        from src.business_layer.parallel_sync_manager import ParallelSyncManager
        
        # ParallelSyncManagerを初期化
        parallel_manager = ParallelSyncManager(max_workers=2)
        
        # 設定値の確認
        assert parallel_manager.get_max_workers() == 2
        
        # 最適ワーカー数の推定テスト
        optimal_workers = parallel_manager.estimate_optimal_workers(5)
        assert optimal_workers == 2  # max_workersが制限
        
        print("✅ ParallelSyncManager実装成功 - 基本機能が動作")
        return True
        
    except Exception as e:
        print(f"❌ ParallelSyncManager実装エラー: {e}")
        return False

def test_metrics_cache():
    """MetricsCache実装テスト"""
    print("\n=== MetricsCache実装テスト ===")
    
    try:
        from src.data_layer.metrics_cache import MetricsCache
        
        # MetricsCacheを初期化
        cache = MetricsCache(default_ttl_seconds=60)
        
        # キャッシュ統計の確認
        stats = cache.get_cache_stats()
        assert stats['total_entries'] == 0
        assert stats['default_ttl_seconds'] == 60
        
        # キャッシュされていない状態の確認
        assert cache.is_cached("test/repo") is False
        
        # データ取得（計算＆キャッシュ）
        result = cache.get_cached_weekly_metrics("test/repo", "UTC")
        assert len(result) == 52  # 52週分のデータ
        
        # キャッシュされた状態の確認
        assert cache.is_cached("test/repo") is True
        
        print("✅ MetricsCache実装成功 - 基本機能が動作")
        return True
        
    except Exception as e:
        print(f"❌ MetricsCache実装エラー: {e}")
        return False

def test_optimized_queries():
    """OptimizedQueries実装テスト"""
    print("\n=== OptimizedQueries実装テスト ===")
    
    try:
        from src.data_layer.optimized_queries import OptimizedQueries
        from unittest.mock import Mock
        
        # モックセッション
        mock_session = Mock()
        
        # OptimizedQueriesを初期化
        optimizer = OptimizedQueries(mock_session)
        
        print("✅ OptimizedQueries実装成功 - 初期化が動作")
        return True
        
    except Exception as e:
        print(f"❌ OptimizedQueries実装エラー: {e}")
        return False

def test_chunked_aggregator():
    """ChunkedAggregator実装テスト"""
    print("\n=== ChunkedAggregator実装テスト ===")
    
    try:
        from src.business_layer.chunked_aggregator import ChunkedAggregator
        
        # ChunkedAggregatorを初期化
        aggregator = ChunkedAggregator(chunk_size=100)
        
        # チャンク処理のテスト
        result = aggregator.calculate_weekly_metrics_chunked(500)
        
        assert result['status'] == 'success'
        assert result['chunks_processed'] == 5  # 500 / 100 = 5チャンク
        assert result['total_records_processed'] == 500
        assert 'processing_time_seconds' in result
        assert 'memory_peak_mb' in result
        
        print("✅ ChunkedAggregator実装成功 - 基本機能が動作")
        return True
        
    except Exception as e:
        print(f"❌ ChunkedAggregator実装エラー: {e}")
        return False

def test_memory_limited_processor():
    """MemoryLimitedProcessor実装テスト"""  
    print("\n=== MemoryLimitedProcessor実装テスト ===")
    
    try:
        from src.business_layer.memory_limited_processor import MemoryLimitedProcessor
        
        # MemoryLimitedProcessorを初期化
        processor = MemoryLimitedProcessor(memory_limit_mb=50)
        
        # メモリ使用量の取得テスト
        memory_info = processor.get_current_memory_usage()
        assert 'rss_mb' in memory_info
        assert memory_info['memory_limit_mb'] == 50
        
        # データセット処理テスト
        result = processor.process_large_dataset()
        
        assert result['status'] == 'success'
        assert result['processed_batches'] == 10
        assert result['total_items_processed'] > 0
        assert result['peak_memory_mb'] <= 50  # メモリ制限を超えていない
        
        print("✅ MemoryLimitedProcessor実装成功 - 基本機能が動作")
        return True
        
    except Exception as e:
        print(f"❌ MemoryLimitedProcessor実装エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("パフォーマンス最適化 TDD GREENフェーズ テスト開始")
    print("=" * 60)
    
    tests = [
        test_batch_processor,
        test_parallel_sync_manager,
        test_metrics_cache,
        test_optimized_queries,
        test_chunked_aggregator,
        test_memory_limited_processor
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"GREENフェーズテスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("✅ すべてのGREENフェーズテストが成功しました - REFACTORフェーズに進む準備ができています")
        return True
    else:
        print("❌ 一部のテストが失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)