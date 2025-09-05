"""CLIコマンドのテスト"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from src.presentation_layer.cli import cli, init, visualize


class TestCLI:
    """CLIコマンドのテスト"""
    
    @pytest.fixture
    def runner(self):
        """Click CLIランナーのフィクスチャ"""
        return CliRunner()
    
    @pytest.fixture
    def mock_config_dir(self):
        """一時設定ディレクトリのフィクスチャ"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config_data(self):
        """モック設定データのフィクスチャ"""
        return {
            'github': {
                'api_token': 'test_token',
                'repositories': ['owner/repo1', 'owner/repo2']
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'test_db'
            },
            'application': {
                'timezone': 'Asia/Tokyo'
            }
        }
    
    def test_CLIグループが正常に定義されている(self, runner):
        """正常系: CLIグループが正常に定義されていることを確認"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'GitHub生産性メトリクス可視化ツール' in result.output
    
    def test_initコマンドが定義されている(self, runner):
        """正常系: initコマンドが定義されていることを確認"""
        result = runner.invoke(cli, ['init', '--help'])
        assert result.exit_code == 0
        assert 'init' in result.output
        assert '初回データ取得' in result.output
    
    def test_visualizeコマンドが定義されている(self, runner):
        """正常系: visualizeコマンドが定義されていることを確認"""
        result = runner.invoke(cli, ['visualize', '--help'])
        assert result.exit_code == 0
        assert 'visualize' in result.output
        assert '可視化のみ実行' in result.output


class TestInitCommand:
    """initコマンドのテスト"""
    
    @pytest.fixture
    def runner(self):
        """Click CLIランナーのフィクスチャ"""
        return CliRunner()
    
    @pytest.fixture
    def mock_sync_result_success(self):
        """成功時のSyncManager結果のフィクスチャ"""
        return {
            'status': 'success',
            'processed_repositories': ['owner/repo1', 'owner/repo2'],
            'total_prs_fetched': 150,
            'sync_duration_seconds': 45.2
        }
    
    @pytest.fixture
    def mock_sync_result_partial(self):
        """部分成功時のSyncManager結果のフィクスチャ"""
        return {
            'status': 'partial_success',
            'processed_repositories': ['owner/repo1'],
            'failed_repositories': ['owner/repo2'],
            'total_prs_fetched': 75,
            'failed_count': 1,
            'sync_duration_seconds': 30.5
        }
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    @patch('src.presentation_layer.cli.SyncManager')
    @patch('src.presentation_layer.cli.GitHubClient')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityAggregator')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_initコマンドが正常に実行される(
        self, mock_timezone_handler, mock_aggregator, mock_db_manager,
        mock_github_client, mock_sync_manager, mock_config_loader,
        runner, mock_sync_result_success
    ):
        """正常系: initコマンドが正常に実行されることを確認"""
        # モック設定
        mock_config_loader.return_value.load_config.return_value = {
            'github': {'api_token': 'test_token', 'repositories': ['owner/repo1']}
        }
        mock_sync_manager.return_value.initial_sync.return_value = mock_sync_result_success
        
        result = runner.invoke(init, ['--days', '90'])
        
        assert result.exit_code == 0
        assert '初期データ同期を開始' in result.output
        assert 'データ同期が完了' in result.output
        assert '150' in result.output  # total_prs_fetched
        
        # SyncManagerが正しい引数で呼び出されることを確認
        mock_sync_manager.return_value.initial_sync.assert_called_once()
        call_args = mock_sync_manager.return_value.initial_sync.call_args
        assert call_args[1]['days_back'] == 90
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    def test_initコマンドで設定ファイルエラーが適切に処理される(
        self, mock_config_loader, runner
    ):
        """異常系: 設定ファイルエラーが適切に処理されることを確認"""
        mock_config_loader.return_value.load_config.side_effect = Exception("Config file not found")
        
        result = runner.invoke(init)
        
        assert result.exit_code == 1
        assert 'エラー' in result.output
        assert 'Config file not found' in result.output
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    @patch('src.presentation_layer.cli.SyncManager')
    @patch('src.presentation_layer.cli.GitHubClient')
    @patch('src.presentation_layer.cli.DatabaseManager')  
    @patch('src.presentation_layer.cli.ProductivityAggregator')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_initコマンドで部分成功が適切に処理される(
        self, mock_timezone_handler, mock_aggregator, mock_db_manager,
        mock_github_client, mock_sync_manager, mock_config_loader,
        runner, mock_sync_result_partial
    ):
        """正常系: 部分成功時に適切なメッセージが表示されることを確認"""
        mock_config_loader.return_value.load_config.return_value = {
            'github': {'api_token': 'test_token', 'repositories': ['owner/repo1', 'owner/repo2']}
        }
        mock_sync_manager.return_value.initial_sync.return_value = mock_sync_result_partial
        
        result = runner.invoke(init)
        
        assert result.exit_code == 0
        assert 'データ同期が部分的に完了' in result.output
        assert '1個のリポジトリで失敗' in result.output
        assert '75' in result.output  # total_prs_fetched
    
    def test_initコマンドのdaysオプションのデフォルト値(self, runner):
        """正常系: daysオプションのデフォルト値が180であることを確認"""
        result = runner.invoke(init, ['--help'])
        assert result.exit_code == 0
        assert 'default: 180' in result.output or '180' in result.output


class TestVisualizeCommand:
    """visualizeコマンドのテスト"""
    
    @pytest.fixture
    def runner(self):
        """Click CLIランナーのフィクスチャ"""
        return CliRunner()
    
    @pytest.fixture
    def mock_weekly_data(self):
        """モック週次データのフィクスチャ"""
        import pandas as pd
        from datetime import datetime, timezone
        return pd.DataFrame({
            'week_start': [
                datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 22, 0, 0, tzinfo=timezone.utc)
            ],
            'week_end': [
                datetime(2024, 1, 21, 23, 59, 59, tzinfo=timezone.utc),
                datetime(2024, 1, 28, 23, 59, 59, tzinfo=timezone.utc)
            ],
            'pr_count': [10, 15],
            'unique_authors': [3, 5],
            'productivity': [3.33, 3.0]
        })
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityVisualizer')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_visualizeコマンドが正常に実行される(
        self, mock_timezone_handler, mock_visualizer, mock_db_manager,
        mock_config_loader, runner, mock_weekly_data
    ):
        """正常系: visualizeコマンドが正常に実行されることを確認"""
        # モック設定
        mock_config_loader.return_value.load_config.return_value = {
            'application': {'timezone': 'Asia/Tokyo'}
        }
        mock_db_manager.return_value.get_weekly_metrics.return_value = mock_weekly_data
        mock_html_content = '<html><div>Mock Chart</div></html>'
        mock_visualizer.return_value.create_productivity_chart.return_value = mock_html_content
        
        result = runner.invoke(visualize)
        
        assert result.exit_code == 0
        assert 'グラフ生成を開始' in result.output
        assert 'グラフが正常に生成されました' in result.output
        
        # ProductivityVisualizerが呼び出されることを確認
        mock_visualizer.return_value.create_productivity_chart.assert_called_once_with(mock_weekly_data)
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    def test_visualizeコマンドで設定ファイルエラーが適切に処理される(
        self, mock_config_loader, runner
    ):
        """異常系: 設定ファイルエラーが適切に処理されることを確認"""
        mock_config_loader.return_value.load_config.side_effect = Exception("Config file not found")
        
        result = runner.invoke(visualize)
        
        assert result.exit_code == 1
        assert 'エラー' in result.output
        assert 'Config file not found' in result.output
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityVisualizer')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_visualizeコマンドで空データが適切に処理される(
        self, mock_timezone_handler, mock_visualizer, mock_db_manager,
        mock_config_loader, runner
    ):
        """正常系: 空データ時に適切なメッセージが表示されることを確認"""
        import pandas as pd
        
        mock_config_loader.return_value.load_config.return_value = {
            'application': {'timezone': 'Asia/Tokyo'}
        }
        empty_data = pd.DataFrame()
        mock_db_manager.return_value.get_weekly_metrics.return_value = empty_data
        
        result = runner.invoke(visualize)
        
        assert result.exit_code == 0
        assert 'データがありません' in result.output
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityVisualizer')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_visualizeコマンドでHTMLファイル保存が確認される(
        self, mock_timezone_handler, mock_visualizer, mock_db_manager,
        mock_config_loader, runner, mock_weekly_data, tmp_path
    ):
        """正常系: HTMLファイルが正しく保存されることを確認"""
        # 一時ディレクトリを出力先として設定
        output_path = tmp_path / "productivity_chart.html"
        
        mock_config_loader.return_value.load_config.return_value = {
            'application': {'timezone': 'Asia/Tokyo'}
        }
        mock_db_manager.return_value.get_weekly_metrics.return_value = mock_weekly_data
        mock_html_content = '<html><div>Mock Chart</div></html>'
        mock_visualizer.return_value.create_productivity_chart.return_value = mock_html_content
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__ = Mock(return_value=mock_file)
            mock_open.return_value.__exit__ = Mock(return_value=None)
            
            result = runner.invoke(visualize)
            
            assert result.exit_code == 0
            # ファイル書き込みが行われたことを確認
            mock_file.write.assert_called_once_with(mock_html_content)


class TestCLIErrorHandling:
    """CLIエラーハンドリングのテスト"""
    
    @pytest.fixture
    def runner(self):
        """Click CLIランナーのフィクスチャ"""
        return CliRunner()
    
    def test_存在しないコマンドでエラーメッセージが表示される(self, runner):
        """異常系: 存在しないコマンドでエラーメッセージが表示されることを確認"""
        result = runner.invoke(cli, ['nonexistent'])
        assert result.exit_code != 0
        assert 'No such command' in result.output
    
    def test_不正なオプションでエラーメッセージが表示される(self, runner):
        """異常系: 不正なオプションでエラーメッセージが表示されることを確認"""
        result = runner.invoke(cli, ['init', '--invalid-option'])
        assert result.exit_code != 0
        assert 'no such option' in result.output.lower()