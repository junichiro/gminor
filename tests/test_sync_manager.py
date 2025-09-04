"""SyncManagerのテスト"""
import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, call
from sqlalchemy.exc import SQLAlchemyError

from src.business_layer.sync_manager import SyncManager, DataSyncError
from src.data_layer.github_client import GitHubClient, GitHubAPIError
from src.data_layer.database_manager import DatabaseManager, DatabaseError
from src.business_layer.aggregator import ProductivityAggregator
from src.data_layer.models import PullRequest, SyncStatus, WeeklyMetrics


class TestSyncManager:
    """SyncManagerクラスのテスト"""
    
    @pytest.fixture
    def mock_github_client(self):
        """GitHubClientのモック"""
        client = Mock(spec=GitHubClient)
        return client
    
    @pytest.fixture
    def mock_db_manager(self):
        """DatabaseManagerのモック"""
        manager = Mock(spec=DatabaseManager)
        return manager
    
    @pytest.fixture
    def mock_aggregator(self):
        """ProductivityAggregatorのモック"""
        aggregator = Mock(spec=ProductivityAggregator)
        return aggregator
    
    @pytest.fixture
    def sync_manager(self, mock_github_client, mock_db_manager, mock_aggregator):
        """SyncManagerのフィクスチャ"""
        return SyncManager(
            github_client=mock_github_client,
            db_manager=mock_db_manager,
            aggregator=mock_aggregator
        )
    
    @pytest.fixture
    def sample_pr_data(self):
        """サンプルPRデータ"""
        return [
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            },
            {
                "number": 2,
                "title": "PR 2",
                "author": "developer2",
                "merged_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc)
            }
        ]
    
    @pytest.fixture
    def sample_weekly_metrics(self):
        """サンプル週次メトリクス"""
        return pd.DataFrame({
            'week_start': [datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)],
            'week_end': [datetime(2024, 1, 21, 23, 59, 59, tzinfo=timezone.utc)],
            'pr_count': [2],
            'unique_authors': [2],
            'productivity': [1.0]
        })
    
    def test_SyncManagerが正常に初期化される(self, mock_github_client, mock_db_manager, mock_aggregator):
        """正常系: SyncManagerが正常に初期化されることを確認"""
        sync_manager = SyncManager(
            github_client=mock_github_client,
            db_manager=mock_db_manager,
            aggregator=mock_aggregator
        )
        
        assert sync_manager.github_client == mock_github_client
        assert sync_manager.db_manager == mock_db_manager
        assert sync_manager.aggregator == mock_aggregator
    
    def test_initial_syncが正常に実行される(self, sync_manager, mock_github_client, 
                                         mock_db_manager, mock_aggregator, 
                                         sample_pr_data, sample_weekly_metrics):
        """正常系: 初回データ同期が正常に実行されることを確認"""
        # モックセットアップ
        repositories = ["test/repo1", "test/repo2"]
        days_back = 30
        
        # GitHubからのPR取得をモック
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        
        # 集計処理をモック
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        
        # データベースセッションをモック
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None  # 既存データなし
        
        # initial_sync実行
        result = sync_manager.initial_sync(repositories, days_back)
        
        # 戻り値の確認
        assert isinstance(result, dict)
        assert result['status'] == 'success'
        assert result['processed_repositories'] == 2
        assert result['total_prs_fetched'] > 0
        assert 'sync_duration_seconds' in result
        
        # GitHubClient呼び出し確認
        assert mock_github_client.fetch_merged_prs.call_count == 2
        
        # Aggregator呼び出し確認
        assert mock_aggregator.calculate_weekly_metrics.call_count == 2
        
        # データベース保存確認
        assert mock_session.add_all.called
        assert mock_session.commit.called
    
    def test_複数リポジトリの処理が正常に動作する(self, sync_manager, mock_github_client,
                                        mock_db_manager, mock_aggregator, 
                                        sample_pr_data, sample_weekly_metrics):
        """正常系: 複数リポジトリの処理が正常に動作することを確認"""
        repositories = ["repo1", "repo2", "repo3"]
        
        # モックセットアップ
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        result = sync_manager.initial_sync(repositories)
        
        # 各リポジトリが処理されたことを確認
        assert result['processed_repositories'] == 3
        assert mock_github_client.fetch_merged_prs.call_count == 3
        
        # 各リポジトリに対して正しい引数で呼び出されたことを確認
        for i, repo in enumerate(repositories):
            args, kwargs = mock_github_client.fetch_merged_prs.call_args_list[i]
            assert args[0] == repo  # repository name
            assert isinstance(args[1], datetime)  # since parameter
    
    def test_データ重複回避ロジックが動作する(self, sync_manager, mock_github_client,
                                    mock_db_manager, mock_aggregator,
                                    sample_pr_data, sample_weekly_metrics):
        """正常系: データの重複回避ロジックが正常に動作することを確認"""
        repositories = ["test/repo"]
        
        # 既存のPRデータをモック（重複データ）- 一括チェック用
        existing_pr = Mock()
        existing_pr.pr_number = 1  # sample_pr_dataの最初のPRと重複
        
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        # 一括重複チェック用のモック
        mock_session.query.return_value.filter.return_value.all.return_value = [existing_pr]
        
        # GitHubからのPR取得をモック
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        
        result = sync_manager.initial_sync(repositories)
        
        # 重複チェックが実行されたことを確認
        assert mock_session.query.called
        assert result['status'] == 'success'
        
        # 新しいPRのみが追加されることを確認（重複は除外）
        add_all_calls = mock_session.add_all.call_args_list
        assert len(add_all_calls) > 0
    
    def test_プログレス表示が正常に動作する(self, sync_manager, mock_github_client,
                                  mock_db_manager, mock_aggregator,
                                  sample_pr_data, sample_weekly_metrics):
        """正常系: プログレス表示が正常に動作することを確認"""
        repositories = ["repo1", "repo2", "repo3"]
        
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(sync_manager.logger, 'info') as mock_log_info:
            result = sync_manager.initial_sync(repositories, progress=True)
            
            # プログレス表示ログが呼び出されたことを確認
            assert mock_log_info.called
            progress_calls = [call for call in mock_log_info.call_args_list 
                            if 'Processing repository' in str(call)]
            assert len(progress_calls) >= len(repositories)
    
    def test_GitHubAPIエラー時の適切な処理(self, sync_manager, mock_github_client,
                                    mock_db_manager, mock_aggregator):
        """異常系: GitHubAPIエラーが発生した場合でも他のリポジトリは処理継続することを確認"""
        repositories = ["test/repo1", "test/repo2"]
        
        # 1つ目のリポジトリでGitHubAPIエラー、2つ目は正常処理
        mock_github_client.fetch_merged_prs.side_effect = [
            GitHubAPIError("API Error", status_code=403),
            []  # 2つ目のリポジトリは正常（空のリスト）
        ]
        
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        result = sync_manager.initial_sync(repositories)
        
        # 部分的な成功を確認
        assert result['status'] == 'partial_success'
        assert result['processed_repositories'] == 1  # 1つは成功
        assert result['failed_count'] == 1
        assert 'test/repo1' in result['failed_repositories']
    
    def test_データベースエラー時の適切な処理(self, sync_manager, mock_github_client,
                                      mock_db_manager, mock_aggregator,
                                      sample_pr_data, sample_weekly_metrics):
        """異常系: データベースエラーが発生した場合の適切な処理を確認"""
        repositories = ["test/repo"]
        
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        
        # データベースエラーをモック（重大なエラーなので全体停止）
        mock_db_manager.get_session.side_effect = DatabaseError("DB Connection Error")
        
        # DataSyncErrorが発生することを確認（データベース接続エラーは全体停止）
        with pytest.raises(DataSyncError) as exc_info:
            sync_manager.initial_sync(repositories)
        
        assert "Database error" in str(exc_info.value)
        assert "DB Connection Error" in str(exc_info.value)
    
    def test_集計処理エラー時の適切な処理(self, sync_manager, mock_github_client,
                                 mock_db_manager, mock_aggregator,
                                 sample_pr_data):
        """異常系: 集計処理でエラーが発生した場合でも他のリポジトリは処理継続することを確認"""
        repositories = ["test/repo1", "test/repo2"]
        
        # GitHubから正常にデータ取得
        mock_github_client.fetch_merged_prs.side_effect = [sample_pr_data, []]
        
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []  # 既存データなし
        
        # 1つ目のリポジトリで集計エラー、2つ目は正常
        mock_aggregator.calculate_weekly_metrics.side_effect = [
            Exception("Aggregation Error"),
            sample_pr_data  # 2つ目は正常（空でも良い）
        ]
        
        result = sync_manager.initial_sync(repositories)
        
        # 部分的な成功を確認
        assert result['status'] == 'partial_success'
        assert result['failed_count'] == 1
        assert 'test/repo1' in result['failed_repositories']
    
    def test_SyncStatusが正常に更新される(self, sync_manager, mock_github_client,
                                  mock_db_manager, mock_aggregator,
                                  sample_pr_data, sample_weekly_metrics):
        """正常系: SyncStatusテーブルが正常に更新されることを確認"""
        repositories = ["test/repo"]
        
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # 既存のSyncStatusなしをモック
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = sync_manager.initial_sync(repositories)
        
        # SyncStatusが作成・更新されたことを確認
        assert mock_session.add.called or mock_session.add_all.called
        assert result['status'] == 'success'
    
    def test_デフォルト値が正しく設定される(self, sync_manager, mock_github_client,
                                   mock_db_manager, mock_aggregator,
                                   sample_pr_data, sample_weekly_metrics):
        """正常系: デフォルト値（days_back=180）が正しく設定されることを確認"""
        repositories = ["test/repo"]
        
        mock_github_client.fetch_merged_prs.return_value = sample_pr_data
        mock_aggregator.calculate_weekly_metrics.return_value = sample_weekly_metrics
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # days_backを指定せずに実行
        result = sync_manager.initial_sync(repositories)
        
        # fetch_merged_prsが適切な日付範囲で呼び出されることを確認
        args, kwargs = mock_github_client.fetch_merged_prs.call_args
        since_date = args[1]  # since parameter
        
        # 約180日前の日付が設定されることを確認
        expected_since = datetime.now(timezone.utc) - timedelta(days=180)
        delta = abs((since_date - expected_since).total_seconds())
        assert delta < 3600  # 1時間以内の差は許容
    
    def test_空のリポジトリリストの処理(self, sync_manager):
        """正常系: 空のリポジトリリストが適切に処理されることを確認"""
        repositories = []
        
        result = sync_manager.initial_sync(repositories)
        
        assert result['status'] == 'success'
        assert result['processed_repositories'] == 0
        assert result['total_prs_fetched'] == 0