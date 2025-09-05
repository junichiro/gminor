#!/usr/bin/env python3
"""パフォーマンス統合テスト - 全体的な性能向上機能の検証"""
import sys
import os
import time
from unittest.mock import Mock

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_performance_optimizer():
    """PerformanceOptimizer統合テスト"""
    print("=== PerformanceOptimizer統合テスト ===")
    
    try:
        from src.business_layer.performance_optimizer import PerformanceOptimizer, PerformanceConfig
        
        # カスタム設定でオプティマイザーを初期化
        config = PerformanceConfig(
            batch_size=50,
            max_workers=2,
            enable_parallel=True,
            enable_chunked_processing=True
        )
        
        optimizer = PerformanceOptimizer(config)
        
        # テストデータを生成
        test_data = [
            {'id': i, 'data': f'test_data_{i}', 'value': i * 2}
            for i in range(1000)  # 1000件のテストデータ
        ]
        
        # 最適化された処理を実行
        result = optimizer.optimize_data_processing(test_data, "integration_test")
        
        # 結果検証
        assert result['status'] == 'success'
        assert result['optimization_applied'] is True
        assert 'strategy_used' in result
        assert 'performance_metrics' in result
        
        # パフォーマンスメトリクスの検証
        metrics = result['performance_metrics']
        assert metrics['records_processed'] == 1000
        assert metrics['throughput_per_second'] > 0
        
        # サマリー取得テスト
        summary = optimizer.get_performance_summary()
        assert summary['total_operations'] == 1
        assert summary['total_records_processed'] == 1000
        
        print(f"✅ 最適化戦略: {result['strategy_used']}")
        print(f"✅ 処理時間: {metrics['processing_time_seconds']:.3f}秒")
        print(f"✅ スループット: {metrics['throughput_per_second']:.1f} records/s")
        print("✅ PerformanceOptimizer統合テスト成功")
        return True
        
    except Exception as e:
        print(f"❌ PerformanceOptimizer統合テストエラー: {e}")
        return False

def test_performance_enhanced_sync_manager():
    """PerformanceEnhancedSyncManager統合テスト"""
    print("\n=== PerformanceEnhancedSyncManager統合テスト ===")
    
    try:
        from src.business_layer.performance_integration import PerformanceEnhancedSyncManager
        from src.business_layer.performance_optimizer import PerformanceConfig
        
        # モックSyncManagerを作成
        mock_sync_manager = Mock()
        mock_sync_manager.initial_sync.return_value = {
            'status': 'success',
            'processed_repositories': 3,
            'total_prs_fetched': 150,
            'sync_duration_seconds': 5.0
        }
        
        # パフォーマンス設定
        config = PerformanceConfig(
            batch_size=2,
            enable_parallel=False,  # 並列処理を無効にしてバッチ処理をテスト
            enable_chunked_processing=True
        )
        
        # 強化版SyncManagerを初期化
        enhanced_sync = PerformanceEnhancedSyncManager(mock_sync_manager, config)
        
        # テストリポジトリリスト
        test_repos = ["repo1", "repo2", "repo3", "repo4", "repo5"]
        
        # 最適化された同期を実行
        result = enhanced_sync.optimized_initial_sync(test_repos, days_back=90)
        
        # 結果検証
        assert result['optimization_applied'] is True
        assert 'performance_stats' in result
        assert result['status'] == 'success'
        
        # 最適化推奨の取得テスト
        recommendations = enhanced_sync.get_optimization_recommendations(test_repos, 2000)
        assert recommendations['repository_count'] == 5
        assert recommendations['estimated_pr_count'] == 2000
        assert len(recommendations['recommendations']) > 0
        
        # パフォーマンスレポート取得テスト
        report = enhanced_sync.get_performance_report()
        assert 'performance_summary' in report
        assert 'batch_processor_config' in report
        
        print(f"✅ 最適化方法: {result['performance_stats']['optimization_method']}")
        print(f"✅ 推奨事項数: {len(recommendations['recommendations'])}")
        print("✅ PerformanceEnhancedSyncManager統合テスト成功")
        return True
        
    except Exception as e:
        print(f"❌ PerformanceEnhancedSyncManager統合テストエラー: {e}")
        return False

def test_pagination_functionality():
    """ページネーション機能テスト"""
    print("\n=== ページネーション機能テスト ===")
    
    try:
        from src.data_layer.database_manager import DatabaseManager
        from unittest.mock import Mock, MagicMock
        
        # モックセッションとクエリ結果を設定
        mock_session = Mock()
        mock_query = Mock()
        mock_base_query = Mock()
        
        # クエリチェーンのモック設定
        mock_session.query.return_value = mock_base_query
        mock_base_query.filter.return_value = mock_base_query
        mock_base_query.count.return_value = 250  # 総件数250件
        mock_base_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # ページ1のテストデータ（10件）
        mock_results = [
            (f'2024-01-{i:02d}', f'user_{i}', i, 'test/repo', f'PR {i}')
            for i in range(1, 11)
        ]
        mock_query.all.return_value = mock_results
        
        # DatabaseManagerのget_sessionをモック
        db_manager = DatabaseManager(':memory:')
        db_manager.get_session = MagicMock()
        db_manager.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        db_manager.get_session.return_value.__exit__ = Mock(return_value=None)
        
        # ページネーション機能をテスト
        result = db_manager.get_merged_pull_requests_paginated(page=1, page_size=10)
        
        # 結果検証
        assert result['page'] == 1
        assert result['page_size'] == 10
        assert result['total_count'] == 250
        assert result['total_pages'] == 25  # 250 / 10 = 25
        assert result['has_next_page'] is True
        assert result['has_prev_page'] is False
        assert len(result['data']) == 10
        assert result['showing_from'] == 1
        assert result['showing_to'] == 10
        
        print(f"✅ ページ情報: {result['page']}/{result['total_pages']}")
        print(f"✅ データ件数: {len(result['data'])}/{result['total_count']}")
        print(f"✅ 次ページ: {result['has_next_page']}, 前ページ: {result['has_prev_page']}")
        print("✅ ページネーション機能テスト成功")
        return True
        
    except Exception as e:
        print(f"❌ ページネーション機能テストエラー: {e}")
        return False

def test_batch_memory_optimization():
    """バッチ処理メモリ最適化テスト"""
    print("\n=== バッチ処理メモリ最適化テスト ===")
    
    try:
        from src.business_layer.batch_processor import BatchProcessor
        
        # メモリ制限付きバッチプロセッサー
        processor = BatchProcessor(batch_size=100, max_memory_mb=10)
        
        # 大量テストデータ
        large_dataset = [{'id': i, 'data': f'data_{i}'} for i in range(2000)]
        
        # メモリ使用量を推定
        estimated_memory = processor.estimate_memory_usage(len(large_dataset), 0.5)  # 0.5KB/record
        
        # メモリ制限に基づいて最適なバッチサイズを計算
        optimal_batch_size = processor.optimize_batch_size_for_memory(len(large_dataset), 0.5)
        
        # バッチ処理を実行
        batches = list(processor.process_prs_in_batches(large_dataset, optimal_batch_size))
        
        # 結果検証
        assert len(batches) > 1  # 複数のバッチに分割されている
        assert optimal_batch_size <= processor.get_batch_size()  # 最適化されたサイズ
        assert estimated_memory > 0  # メモリ推定が動作
        
        # すべてのデータが処理されていることを確認
        total_processed = sum(len(batch) for batch in batches)
        assert total_processed == len(large_dataset)
        
        print(f"✅ 推定メモリ使用量: {estimated_memory:.2f}MB")
        print(f"✅ 最適バッチサイズ: {optimal_batch_size}")
        print(f"✅ バッチ数: {len(batches)}")
        print(f"✅ 処理データ総数: {total_processed}")
        print("✅ バッチ処理メモリ最適化テスト成功")
        return True
        
    except Exception as e:
        print(f"❌ バッチ処理メモリ最適化テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("パフォーマンス最適化統合テスト開始")
    print("=" * 60)
    
    tests = [
        test_performance_optimizer,
        test_performance_enhanced_sync_manager,
        test_pagination_functionality,
        test_batch_memory_optimization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"統合テスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("✅ すべての統合テストが成功しました - 実装完了準備OK")
        return True
    else:
        print("❌ 一部のテストが失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)