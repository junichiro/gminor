"""MetricsServiceのテスト"""
import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.business_layer.metrics_service import MetricsService, MetricsServiceError
from src.data_layer.database_manager import DatabaseError


class TestMetricsService:
    """MetricsServiceクラスのテスト"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """DatabaseManagerのモック"""
        return Mock()
    
    @pytest.fixture
    def mock_timezone_handler(self):
        """TimezoneHandlerのモック"""
        return Mock()
    
    @pytest.fixture
    def metrics_service(self, mock_db_manager, mock_timezone_handler):
        """MetricsServiceのフィクスチャ"""
        return MetricsService(mock_db_manager, mock_timezone_handler)
    
    @pytest.fixture
    def sample_pr_data(self):
        """サンプルプルリクエストデータ"""
        return [
            {
                'merged_at': datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                'author': 'user1',
                'number': 1
            },
            {
                'merged_at': datetime(2024, 1, 16, 10, 0, tzinfo=timezone.utc),
                'author': 'user2',
                'number': 2
            },
            {
                'merged_at': datetime(2024, 1, 22, 10, 0, tzinfo=timezone.utc),
                'author': 'user1',
                'number': 3
            }
        ]
    
    @pytest.fixture
    def sample_weekly_metrics(self):
        """サンプル週次メトリクス"""
        return pd.DataFrame({
            'week_start': [
                datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 22, 0, 0, tzinfo=timezone.utc)
            ],
            'week_end': [
                datetime(2024, 1, 21, 23, 59, 59, tzinfo=timezone.utc),
                datetime(2024, 1, 28, 23, 59, 59, tzinfo=timezone.utc)
            ],
            'pr_count': [2, 1],
            'unique_authors': [2, 1],
            'productivity': [1.0, 1.0]
        })
    
    def test_MetricsServiceが正常に初期化される(self, mock_db_manager, mock_timezone_handler):
        """正常系: MetricsServiceが正常に初期化されることを確認"""
        service = MetricsService(mock_db_manager, mock_timezone_handler)
        assert service.db_manager == mock_db_manager
        assert service.timezone_handler == mock_timezone_handler
        assert service.aggregator is not None
    
    def test_get_weekly_metricsが正常にデータを返す(
        self, metrics_service, sample_pr_data, sample_weekly_metrics
    ):
        """正常系: get_weekly_metricsが正常に週次メトリクスを返すことを確認"""
        # モック設定
        metrics_service.db_manager.get_merged_pull_requests.return_value = sample_pr_data
        metrics_service.aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        
        result = metrics_service.get_weekly_metrics()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity']
        
        # メソッドが呼ばれたことを確認
        metrics_service.db_manager.get_merged_pull_requests.assert_called_once()
        metrics_service.aggregator.calculate_weekly_metrics.assert_called_once_with(sample_pr_data)
    
    def test_get_weekly_metricsで空データが適切に処理される(self, metrics_service):
        """正常系: 空データ時に適切な空のDataFrameが返されることを確認"""
        # 空データを返すモック
        metrics_service.db_manager.get_merged_pull_requests.return_value = []
        
        result = metrics_service.get_weekly_metrics()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity']
    
    def test_get_weekly_metricsでDatabaseErrorが適切に処理される(self, metrics_service):
        """異常系: DatabaseErrorがMetricsServiceErrorとして再発生することを確認"""
        # DatabaseErrorを発生させるモック
        metrics_service.db_manager.get_merged_pull_requests.side_effect = DatabaseError("DB connection failed")
        
        with pytest.raises(MetricsServiceError) as exc_info:
            metrics_service.get_weekly_metrics()
        
        assert "Database error while retrieving pull request data" in str(exc_info.value)
        assert exc_info.value.__cause__.__class__.__name__ == "DatabaseError"
    
    def test_get_weekly_metricsで予期しないエラーが適切に処理される(self, metrics_service):
        """異常系: 予期しないエラーがMetricsServiceErrorとして処理されることを確認"""
        # 予期しないエラーを発生させるモック
        metrics_service.aggregator.calculate_weekly_metrics.side_effect = ValueError("Invalid data")
        metrics_service.db_manager.get_merged_pull_requests.return_value = [{'invalid': 'data'}]
        
        with pytest.raises(MetricsServiceError) as exc_info:
            metrics_service.get_weekly_metrics()
        
        assert "Unexpected error while calculating weekly metrics" in str(exc_info.value)
    
    def test_get_metrics_summaryが正常にサマリーを返す(
        self, metrics_service, sample_pr_data, sample_weekly_metrics
    ):
        """正常系: get_metrics_summaryが正常にメトリクス概要を返すことを確認"""
        # モック設定
        metrics_service.db_manager.get_merged_pull_requests.return_value = sample_pr_data
        metrics_service.aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        
        result = metrics_service.get_metrics_summary()
        
        assert isinstance(result, dict)
        assert result['total_weeks'] == 2
        assert result['total_prs'] == 3  # 2 + 1
        assert result['average_productivity'] == 1.0  # (1.0 + 1.0) / 2
        assert result['max_productivity'] == 1.0
        assert result['min_productivity'] == 1.0
    
    def test_get_metrics_summaryで空データが適切に処理される(self, metrics_service):
        """正常系: 空データ時に適切なゼロサマリーが返されることを確認"""
        # 空データを返すモック
        metrics_service.db_manager.get_merged_pull_requests.return_value = []
        
        result = metrics_service.get_metrics_summary()
        
        assert isinstance(result, dict)
        assert result['total_weeks'] == 0
        assert result['total_prs'] == 0
        assert result['average_productivity'] == 0.0
        assert result['max_productivity'] == 0.0
        assert result['min_productivity'] == 0.0
    
    def test_get_metrics_summaryでエラーが適切に処理される(self, metrics_service):
        """異常系: エラー時にMetricsServiceErrorが発生することを確認"""
        # エラーを発生させるモック
        metrics_service.db_manager.get_merged_pull_requests.side_effect = Exception("Unexpected error")
        
        with pytest.raises(MetricsServiceError) as exc_info:
            metrics_service.get_metrics_summary()
        
        assert "Failed to generate metrics summary" in str(exc_info.value)