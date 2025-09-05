"""CLIコマンドのテスト"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from src.presentation_layer.cli import cli, init, visualize, fetch, stats, cleanup, config


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
    @patch('src.presentation_layer.cli.MetricsService')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityVisualizer')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_visualizeコマンドが正常に実行される(
        self, mock_timezone_handler, mock_visualizer, mock_db_manager,
        mock_metrics_service, mock_config_loader, runner, mock_weekly_data
    ):
        """正常系: visualizeコマンドが正常に実行されることを確認"""
        # モック設定
        mock_config_loader.return_value.load_config.return_value = {
            'application': {'timezone': 'Asia/Tokyo'}
        }
        mock_metrics_service.return_value.get_weekly_metrics.return_value = mock_weekly_data
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
    @patch('src.presentation_layer.cli.MetricsService')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityVisualizer')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_visualizeコマンドで空データが適切に処理される(
        self, mock_timezone_handler, mock_visualizer, mock_db_manager,
        mock_metrics_service, mock_config_loader, runner
    ):
        """正常系: 空データ時に適切なメッセージが表示されることを確認"""
        import pandas as pd
        
        mock_config_loader.return_value.load_config.return_value = {
            'application': {'timezone': 'Asia/Tokyo'}
        }
        empty_data = pd.DataFrame()
        mock_metrics_service.return_value.get_weekly_metrics.return_value = empty_data
        
        result = runner.invoke(visualize)
        
        assert result.exit_code == 0
        assert 'データがありません' in result.output
    
    @patch('src.presentation_layer.cli.ConfigLoader')
    @patch('src.presentation_layer.cli.MetricsService')
    @patch('src.presentation_layer.cli.DatabaseManager')
    @patch('src.presentation_layer.cli.ProductivityVisualizer')
    @patch('src.presentation_layer.cli.TimezoneHandler')
    def test_visualizeコマンドでHTMLファイル保存が確認される(
        self, mock_timezone_handler, mock_visualizer, mock_db_manager,
        mock_metrics_service, mock_config_loader, runner, mock_weekly_data, tmp_path
    ):
        """正常系: HTMLファイルが正しく保存されることを確認"""        
        mock_config_loader.return_value.load_config.return_value = {
            'application': {'timezone': 'Asia/Tokyo'}
        }
        mock_metrics_service.return_value.get_weekly_metrics.return_value = mock_weekly_data
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


class TestAdditionalCLICommands:
    """追加CLIコマンドのテスト"""
    
    @pytest.fixture
    def runner(self):
        """Click CLIランナーのフィクスチャ"""
        return CliRunner()
    
    @pytest.fixture
    def mock_components(self):
        """モックコンポーネントのフィクスチャ"""
        return (
            Mock(),  # timezone_handler
            Mock(),  # github_client
            Mock(),  # db_manager
            Mock()   # aggregator
        )
    
    @pytest.fixture
    def mock_services(self):
        """モックサービスのフィクスチャ"""
        return {
            'sync_manager': Mock(),
            'metrics_service': Mock(),
            'visualizer': Mock()
        }
    
    @pytest.fixture
    def mock_config(self):
        """モック設定のフィクスチャ"""
        return {
            'github': {
                'api_token': 'test_token',
                'repositories': ['owner/repo1', 'owner/repo2']
            },
            'database': {
                'name': 'test_db'
            },
            'application': {
                'timezone': 'Asia/Tokyo',
                'output': {
                    'directory': 'output',
                    'filename': 'chart.html'
                }
            }
        }
    
    # fetchコマンドのテスト
    def test_fetchコマンドが期間指定で実行される(self, runner, mock_components, mock_services, mock_config):
        """正常系: fetchコマンドが期間指定で正常に実行されることを確認"""
        with patch('src.presentation_layer.cli.load_config_and_validate', return_value=mock_config):
            with patch('src.presentation_layer.cli.create_components', return_value=mock_components):
                with patch('src.presentation_layer.cli.create_services_from_components', return_value=mock_services):
                    # モックの設定
                    mock_services['sync_manager'].fetch_period_data.return_value = {
                        'status': 'success',
                        'fetched_prs': 50,
                        'duration_seconds': 5.2
                    }
                    
                    result = runner.invoke(cli, ['fetch', '--from', '2024-01-01', '--to', '2024-01-31'])
                    
                    assert result.exit_code == 0
                    assert '特定期間のデータ取得を開始' in result.output
                    assert '期間: 2024-01-01 〜 2024-01-31' in result.output
                    assert 'データ取得が完了しました' in result.output
                    
                    # 正しい引数で呼び出されたことを確認
                    mock_services['sync_manager'].fetch_period_data.assert_called_once_with(
                        mock_config['github']['repositories'],
                        '2024-01-01',
                        '2024-01-31'
                    )
    
    def test_fetchコマンドが日付形式をバリデートする(self, runner):
        """異常系: fetchコマンドが不正な日付形式をバリデートすることを確認"""
        result = runner.invoke(cli, ['fetch', '--from', 'invalid-date', '--to', '2024-01-31'])
        
        assert result.exit_code != 0
        assert '日付形式が正しくありません' in result.output
    
    # statsコマンドのテスト
    def test_statsコマンドが統計情報を表示する(self, runner, mock_components, mock_services, mock_config):
        """正常系: statsコマンドが統計情報を正しく表示することを確認"""
        with patch('src.presentation_layer.cli.load_config_and_validate', return_value=mock_config):
            with patch('src.presentation_layer.cli.create_components', return_value=mock_components):
                with patch('src.presentation_layer.cli.create_services_from_components', return_value=mock_services):
                    # モックの設定
                    mock_services['metrics_service'].get_metrics_summary.return_value = {
                        'total_weeks': 10,
                        'total_prs': 150,
                        'average_productivity': 3.5,
                        'max_productivity': 5.0,
                        'min_productivity': 1.5
                    }
                    
                    mock_services['metrics_service'].get_repository_stats.return_value = {
                        'owner/repo1': {'pr_count': 80, 'unique_authors': 5},
                        'owner/repo2': {'pr_count': 70, 'unique_authors': 8}
                    }
                    
                    result = runner.invoke(cli, ['stats'])
                    
                    assert result.exit_code == 0
                    assert '📊 統計情報' in result.output
                    assert '総集計期間: 10週' in result.output
                    assert '総PR数: 150' in result.output
                    assert '平均生産性: 3.50' in result.output
                    assert '最高生産性: 5.00' in result.output
                    assert '最低生産性: 1.50' in result.output
                    assert 'リポジトリ別統計' in result.output
                    assert 'owner/repo1' in result.output
                    assert 'owner/repo2' in result.output
    
    # cleanupコマンドのテスト
    def test_cleanupコマンドが古いデータを削除する(self, runner, mock_components, mock_services, mock_config):
        """正常系: cleanupコマンドが指定日付以前のデータを削除することを確認"""
        with patch('src.presentation_layer.cli.load_config_and_validate', return_value=mock_config):
            with patch('src.presentation_layer.cli.create_components', return_value=mock_components):
                with patch('src.presentation_layer.cli.create_services_from_components', return_value=mock_services):
                    # モックの設定
                    mock_components[2].cleanup_old_data.return_value = {
                        'deleted_prs': 100,
                        'deleted_metrics': 20
                    }
                    
                    result = runner.invoke(cli, ['cleanup', '--before', '2023-01-01', '--yes'])
                    
                    assert result.exit_code == 0
                    assert 'データベースのクリーンアップを開始' in result.output
                    assert '2023-01-01 以前のデータを削除' in result.output
                    assert '削除されたPR: 100件' in result.output
                    assert '削除されたメトリクス: 20件' in result.output
                    assert 'クリーンアップが完了しました' in result.output
                    
                    # 正しい引数で呼び出されたことを確認
                    mock_components[2].cleanup_old_data.assert_called_once_with('2023-01-01')
    
    def test_cleanupコマンドが確認プロンプトを表示する(self, runner):
        """正常系: cleanupコマンドが実行前に確認プロンプトを表示することを確認"""
        result = runner.invoke(cli, ['cleanup', '--before', '2023-01-01'], input='n\n')
        
        assert result.exit_code == 0
        assert '本当に削除しますか？' in result.output
        assert 'キャンセルされました' in result.output
    
    # configコマンドのテスト
    def test_configコマンドが現在の設定を表示する(self, runner, mock_config):
        """正常系: configコマンドが現在の設定を表示することを確認"""
        with patch('src.presentation_layer.cli.load_config_and_validate', return_value=mock_config):
            result = runner.invoke(cli, ['config'])
            
            assert result.exit_code == 0
            assert '📋 現在の設定' in result.output
            assert 'リポジトリ' in result.output
            assert '- owner/repo1' in result.output
            assert '- owner/repo2' in result.output
            assert 'タイムゾーン: Asia/Tokyo' in result.output
            assert 'データベース: test_db' in result.output
            assert '出力ディレクトリ: output' in result.output
    
    def test_configコマンドでvalidateオプションが動作する(self, runner, mock_config):
        """正常系: configコマンドのvalidateオプションが設定を検証することを確認"""
        with patch('src.presentation_layer.cli.load_config_and_validate', return_value=mock_config):
            with patch('src.presentation_layer.cli.validate_config', return_value=True) as mock_validate:
                result = runner.invoke(cli, ['config', '--validate'])
                
                assert result.exit_code == 0
                assert '✅ 設定は正常です' in result.output
                mock_validate.assert_called_once_with(mock_config)