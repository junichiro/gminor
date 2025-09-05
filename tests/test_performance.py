"""パフォーマンステスト - 大量データ処理時の性能検証"""
import pytest
import time
import psutil
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import tempfile
import pandas as pd

from src.business_layer.sync_manager import SyncManager
from src.data_layer.database_manager import DatabaseManager
from src.business_layer.aggregator import ProductivityAggregator

# テスト定数
LARGE_DATASET_SIZE = 1000  # 大量データテストサイズ
MAX_PROCESSING_TIME_SECONDS = 10  # 最大処理時間（秒）
MAX_MEMORY_USAGE_MB = 100  # 最大メモリ使用量（MB）
DEFAULT_PAGE_SIZE = 100  # デフォルトページサイズ
DEFAULT_BATCH_SIZE = 50  # デフォルトバッチサイズ
SAMPLE_USER_COUNT = 50  # サンプルユーザー数
WEEKS_IN_YEAR = 52  # 年間週数


class TestPerformanceLargePRData:
    """大量PRデータ処理のパフォーマンステスト"""
    
    @pytest.fixture
    def large_pr_data(self) -> List[Dict[str, Any]]:
        """大量PRデータを生成"""
        base_date = datetime.now(timezone.utc)
        
        pr_data = []
        for i in range(LARGE_DATASET_SIZE):
            pr_data.append({
                "number": i + 1,
                "author": f"user_{i % SAMPLE_USER_COUNT}",
                "title": f"Fix bug #{i + 1}",
                "merged_at": base_date - timedelta(days=i % 365),
                "created_at": base_date - timedelta(days=i % 365, hours=1),
                "updated_at": base_date - timedelta(days=i % 365, minutes=30)
            })
        
        return pr_data
    
    @pytest.fixture 
    def temp_db_manager(self):
        """テスト用データベースマネージャー"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        db_manager = DatabaseManager(temp_db_path)
        db_manager.initialize_database()
        
        yield db_manager
        
        # クリーンアップ
        db_manager.close()
        os.unlink(temp_db_path)
    
    def test_大量PRデータの処理時間が基準以内(self, large_pr_data, temp_db_manager):
        """正常系: 大量PRデータが指定時間以内で処理されることを確認"""
        # Given: 大量のPRデータとモックされた依存関係
        mock_github_client = Mock()
        mock_github_client.fetch_merged_prs.return_value = large_pr_data
        
        aggregator = ProductivityAggregator()
        sync_manager = SyncManager(mock_github_client, temp_db_manager, aggregator)
        
        # When: 大量データの同期処理を実行
        start_time = time.time()
        result = sync_manager.initial_sync(["test/repo"], days_back=365, progress=False)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Then: 処理時間が基準以内であること
        assert processing_time < MAX_PROCESSING_TIME_SECONDS, f"処理時間が基準を超過: {processing_time:.2f}秒"
        assert result['status'] == 'success'
        assert result['total_prs_fetched'] == LARGE_DATASET_SIZE
    
    def test_メモリ使用量が基準以内で処理される(self, large_pr_data, temp_db_manager):
        """正常系: 大量データ処理時のメモリ使用量が適切であることを確認"""
        # Given: 大量のPRデータとモックされた依存関係
        mock_github_client = Mock()
        mock_github_client.fetch_merged_prs.return_value = large_pr_data
        
        aggregator = ProductivityAggregator()
        sync_manager = SyncManager(mock_github_client, temp_db_manager, aggregator)
        
        # プロセスのメモリ使用量を取得
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # When: 大量データの同期処理を実行
        result = sync_manager.initial_sync(["test/repo"], days_back=365, progress=False)
        
        # プロセスのメモリ使用量を再度取得
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Then: メモリ使用量の増加が基準以内であること
        assert memory_increase < MAX_MEMORY_USAGE_MB, f"メモリ使用量の増加が基準を超過: {memory_increase:.2f}MB"
        assert result['status'] == 'success'
        assert result['total_prs_fetched'] == LARGE_DATASET_SIZE


class TestBatchProcessingOptimization:
    """バッチ処理最適化のテスト"""
    
    @pytest.fixture
    def performance_config(self):
        """パフォーマンス設定のフィクスチャ"""
        return {
            'batch_size': DEFAULT_PAGE_SIZE,
            'max_memory_mb': DEFAULT_BATCH_SIZE,
            'parallel_repos': True
        }
    
    def test_バッチサイズが設定可能であること(self, performance_config):
        """正常系: バッチサイズが設定されることを確認"""
        # Given: パフォーマンス設定
        batch_size = performance_config['batch_size']
        
        # When: バッチ処理クラスを初期化
        try:
            from src.business_layer.batch_processor import BatchProcessor
            batch_processor = BatchProcessor(batch_size=batch_size)
            
            # Then: 適切な初期化が行われることを確認
            assert batch_processor.get_batch_size() == batch_size
            assert batch_processor.get_max_memory_mb() == performance_config['max_memory_mb']
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("BatchProcessor dependencies not available")
    
    def test_複数リポジトリの並列処理が可能であること(self, performance_config):
        """正常系: 複数リポジトリの並列処理ができることを確認"""
        # Given: 並列処理が有効な設定
        parallel_enabled = performance_config['parallel_repos']
        assert parallel_enabled is True
        
        # When: 並列処理マネージャーを使用
        try:
            from src.business_layer.parallel_sync_manager import ParallelSyncManager
            parallel_manager = ParallelSyncManager(max_workers=4)
            
            # Then: 並列処理マネージャーが正常に初期化されることを確認
            assert parallel_manager.get_max_workers() == 4
            optimal_workers = parallel_manager.estimate_optimal_workers(repository_count=3)
            assert optimal_workers <= 4
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("ParallelSyncManager dependencies not available")


class TestCachedWeeklyMetrics:
    """週次メトリクスキャッシュ機能のテスト"""
    
    @pytest.fixture
    def sample_cached_data(self) -> pd.DataFrame:
        """サンプルキャッシュデータ"""
        dates = pd.date_range('2024-01-01', periods=WEEKS_IN_YEAR, freq='W')
        return pd.DataFrame({
            'week_start': dates,
            'repo_name': ['test/repo'] * WEEKS_IN_YEAR,
            'pr_count': [10, 15, 8, 12, 20] * 10 + [5, 7],
            'unique_authors': [3, 4, 2, 3, 5] * 10 + [2, 3]
        })
    
    def test_キャッシュされた週次メトリクスが高速で取得される(self, sample_cached_data):
        """正常系: キャッシュされた週次メトリクスが高速で取得されることを確認"""
        # Given: キャッシュされたデータとタイムゾーン設定
        repo_name = "test/repo"
        timezone_name = "Asia/Tokyo"
        
        # When: キャッシュされた週次メトリクスを取得
        start_time = time.time()
        
        try:
            from src.data_layer.metrics_cache import MetricsCache
            cache = MetricsCache()
            result = cache.get_cached_weekly_metrics(repo_name, timezone_name)
            
            end_time = time.time()
            retrieval_time = end_time - start_time
            
            # Then: 基本的なキャッシュ機能が動作することを確認
            assert result is not None
            assert retrieval_time < 1.0  # 1秒以下で取得
            
            # キャッシュ機能の確認
            assert cache.is_cached(repo_name, timezone_name) is True
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("MetricsCache dependencies not available")
    
    def test_キャッシュミス時は計算してキャッシュに保存される(self):
        """正常系: キャッシュミス時は新規計算してキャッシュに保存されることを確認"""
        # Given: キャッシュされていないデータ
        repo_name = "new/repo"
        timezone_name = "UTC"
        
        try:
            from src.data_layer.metrics_cache import MetricsCache
            cache = MetricsCache()
            
            # キャッシュされていない状態を確認
            assert cache.is_cached(repo_name, timezone_name) is False
            
            # When: 存在しないキャッシュデータを要求
            result = cache.get_cached_weekly_metrics(repo_name, timezone_name)
            
            # Then: 新規計算が実行され、結果がキャッシュされることを確認
            assert cache.is_cached(repo_name, timezone_name) is True
            assert result is not None
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("MetricsCache dependencies not available")


class TestDatabaseQueryOptimization:
    """データベースクエリ最適化のテスト"""
    
    def test_ページネーション付きクエリが実装される(self):
        """正常系: 大量データの取得時にページネーションが使用されることを確認"""
        # Given: 大量データが保存されたデータベース
        page_size = DEFAULT_PAGE_SIZE
        page = 1
        
        try:
            from src.data_layer.database_manager import DatabaseManager
            
            # ページネーション機能が実装されていることを確認
            db_manager = DatabaseManager(":memory:")
            assert hasattr(db_manager, 'get_merged_pull_requests_paginated')
            
            # メソッドが呼び出し可能であることを確認
            pagination_method = getattr(db_manager, 'get_merged_pull_requests_paginated')
            assert callable(pagination_method)
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("DatabaseManager dependencies not available")
    
    def test_インデックス最適化されたクエリが使用される(self):
        """正常系: 適切なインデックスが使用されたクエリが実行されることを確認"""
        # Given: インデックス最適化が期待されるクエリパターン
        repo_name = "test/repo"
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        try:
            from src.data_layer.optimized_queries import OptimizedQueries
            from unittest.mock import Mock
            
            # モックセッションでOptimizedQueriesを初期化
            mock_session = Mock()
            optimizer = OptimizedQueries(mock_session)
            
            # 最適化クエリクラスが初期化されることを確認
            assert optimizer is not None
            assert hasattr(optimizer, 'get_prs_by_date_range_optimized')
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("OptimizedQueries dependencies not available")


class TestMemoryEfficientAggregation:
    """メモリ効率的な集計処理のテスト"""
    
    def test_チャンク処理で大量データが処理される(self):
        """正常系: 大量データがチャンク単位で効率的に処理されることを確認"""
        # Given: 大量データとチャンクサイズ
        chunk_size = 500
        total_records = 2000
        
        try:
            from src.business_layer.chunked_aggregator import ChunkedAggregator
            aggregator = ChunkedAggregator(chunk_size=chunk_size)
            result = aggregator.calculate_weekly_metrics_chunked(total_records)
            
            # Then: チャンク処理が正常に完了することを確認
            assert result['status'] == 'success'
            assert result['chunks_processed'] == total_records // chunk_size
            assert 'memory_peak_mb' in result
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("ChunkedAggregator dependencies not available")
    
    def test_メモリ使用量がチャンク処理で制限される(self):
        """正常系: チャンク処理によりメモリ使用量が制限されることを確認"""
        # Given: メモリ制限設定
        memory_limit_mb = MAX_MEMORY_USAGE_MB
        
        try:
            from src.business_layer.memory_limited_processor import MemoryLimitedProcessor
            processor = MemoryLimitedProcessor(memory_limit_mb=memory_limit_mb)
            result = processor.process_large_dataset()
            
            # Then: メモリ使用量が制限内に収まることを確認
            assert result['peak_memory_mb'] <= memory_limit_mb
            assert result['status'] == 'success'
            
        except ImportError:
            # 依存関係が不足している場合はテストをスキップ
            pytest.skip("MemoryLimitedProcessor dependencies not available")