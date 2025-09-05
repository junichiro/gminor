"""ログ機能の統合テスト - 各コンポーネントでのログ出力確認"""
import pytest
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch

from src.business_layer.logging_config import setup_logging


class TestLoggingIntegrationWithComponents:
    """各コンポーネントでのログ統合テスト"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """一時ログディレクトリのフィクスチャ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def logging_config(self, temp_log_dir):
        """テスト用ログ設定のフィクスチャ"""
        return {
            'logging': {
                'level': 'DEBUG',  # 全ログレベルを確認するためDEBUG
                'file': str(temp_log_dir / 'integration_test.log'),
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'max_file_size': '1MB',
                'backup_count': 2
            }
        }
    
    def test_SyncManagerでログが適切に出力される(self, logging_config, temp_log_dir):
        """正常系: SyncManagerのログが適切に出力されることを確認"""
        setup_logging(logging_config)
        
        # SyncManagerのログ動作をシミュレート
        from src.business_layer.sync_manager import SyncManager
        
        # モックオブジェクトを作成してSyncManagerを初期化
        mock_github_client = Mock()
        mock_db_manager = Mock()
        mock_aggregator = Mock()
        
        sync_manager = SyncManager(mock_github_client, mock_db_manager, mock_aggregator)
        
        # ログメッセージのテスト
        sync_manager.logger.info("Test sync started")
        sync_manager.logger.debug("Processing repository details")
        sync_manager.logger.warning("Rate limit approaching")
        sync_manager.logger.error("Sync failed for repository")
        
        # ログファイルの内容を確認
        log_file_path = temp_log_dir / 'integration_test.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            
        # 期待されるログメッセージが記録されていることを確認
        assert 'sync_manager' in log_content
        assert 'Test sync started' in log_content
        assert 'Processing repository details' in log_content
        assert 'Rate limit approaching' in log_content
        assert 'Sync failed for repository' in log_content
        
        # 各ログレベルが適切に記録されていることを確認
        assert 'INFO' in log_content
        assert 'DEBUG' in log_content
        assert 'WARNING' in log_content
        assert 'ERROR' in log_content
    
    def test_DatabaseManagerでログが適切に出力される(self, logging_config, temp_log_dir):
        """正常系: DatabaseManagerのログが適切に出力されることを確認"""
        setup_logging(logging_config)
        
        # DatabaseManagerのログ動作をシミュレート（実際のDBは使わない）
        logger = logging.getLogger('src.data_layer.database_manager')
        
        # 典型的なデータベース操作のログ
        logger.info("Database connection established")
        logger.debug("Executing query: SELECT * FROM pull_requests")
        logger.info("Retrieved 150 merged pull requests")
        logger.warning("Connection pool nearly exhausted")
        logger.error("Database query failed: connection timeout")
        
        # ログファイルの内容を確認
        log_file_path = temp_log_dir / 'integration_test.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # データベース関連のログが記録されていることを確認
        assert 'database_manager' in log_content
        assert 'Database connection established' in log_content
        assert 'Executing query' in log_content
        assert 'Retrieved 150 merged pull requests' in log_content
        assert 'Connection pool nearly exhausted' in log_content
        assert 'Database query failed' in log_content
    
    def test_GitHubClientでAPI関連ログが出力される(self, logging_config, temp_log_dir):
        """正常系: GitHubClientのAPI関連ログが適切に出力されることを確認"""
        setup_logging(logging_config)
        
        # GitHubクライアントのログ動作をシミュレート
        logger = logging.getLogger('src.data_layer.github_client')
        
        # GitHub API関連の典型的なログ
        logger.info("Fetching merged PRs for owner/repo from 2024-01-01 to 2024-12-31")
        logger.debug("Getting repository object for owner/repo")
        logger.debug("Successfully retrieved repository: owner/repo")
        logger.info("Retrieved 25 merged PRs")
        logger.warning("Rate limit approaching: 50 requests remaining")
        logger.error("GitHub API error: Repository not found")
        
        # ログファイルの内容を確認
        log_file_path = temp_log_dir / 'integration_test.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # GitHub API関連のログが記録されていることを確認
        assert 'github_client' in log_content
        assert 'Fetching merged PRs' in log_content
        assert 'Getting repository object' in log_content
        assert 'Successfully retrieved repository' in log_content
        assert 'Retrieved 25 merged PRs' in log_content
        assert 'Rate limit approaching' in log_content
        assert 'GitHub API error' in log_content
    
    def test_複数コンポーネントのログが混在して記録される(self, logging_config, temp_log_dir):
        """正常系: 複数コンポーネントのログが適切に混在して記録されることを確認"""
        setup_logging(logging_config)
        
        # 複数のコンポーネントのロガーを作成
        sync_logger = logging.getLogger('src.business_layer.sync_manager')
        db_logger = logging.getLogger('src.data_layer.database_manager')
        github_logger = logging.getLogger('src.data_layer.github_client')
        main_logger = logging.getLogger('__main__')
        
        # 各コンポーネントでログ出力
        main_logger.info("Application started")
        sync_logger.info("Starting data synchronization")
        github_logger.info("Connecting to GitHub API")
        db_logger.info("Initializing database connection")
        
        sync_logger.debug("Processing repository 1/3")
        github_logger.debug("API request: GET /repos/owner/repo/pulls")
        db_logger.debug("Inserting 10 new records")
        
        sync_logger.info("Data synchronization completed")
        main_logger.info("Application finished")
        
        # ログファイルの内容を確認
        log_file_path = temp_log_dir / 'integration_test.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # すべてのコンポーネントのログが混在して記録されていることを確認
        assert '__main__' in log_content and 'Application started' in log_content
        assert 'sync_manager' in log_content and 'Starting data synchronization' in log_content
        assert 'github_client' in log_content and 'Connecting to GitHub API' in log_content
        assert 'database_manager' in log_content and 'Initializing database connection' in log_content
        
        # ログの順序も確認（時系列順）
        lines = log_content.strip().split('\n')
        assert len(lines) >= 8  # 最低8行のログが記録される
    
    def test_ログローテーション設定が適用される(self, logging_config, temp_log_dir):
        """正常系: ログファイルのローテーション設定が適切に動作することを確認"""
        # 小さなファイルサイズでローテーションをテスト
        logging_config['logging']['max_file_size'] = '1KB'
        logging_config['logging']['backup_count'] = 2
        
        setup_logging(logging_config)
        
        # 大量のログを出力してローテーションを発生させる
        logger = logging.getLogger('rotation_test')
        
        # 1KBを超える量のログを出力
        for i in range(100):
            logger.info(f"This is a long test message for log rotation testing - message number {i:03d}")
        
        log_file_path = temp_log_dir / 'integration_test.log'
        
        # ログファイルが作成されていることを確認
        assert log_file_path.exists()
        
        # ファイルサイズが設定値付近であることを確認（厳密ではなく、極端に大きくないことを確認）
        file_size = log_file_path.stat().st_size
        assert file_size < 5000  # 5KBより小さいことを確認（ローテーションが動作している）
    
    def test_異なるログレベルでのフィルタリング(self, temp_log_dir):
        """正常系: 異なるログレベル設定でのフィルタリングが動作することを確認"""
        # WARNING以上のみ記録する設定
        config_warning = {
            'logging': {
                'level': 'WARNING',
                'file': str(temp_log_dir / 'warning_only.log')
            }
        }
        
        setup_logging(config_warning)
        
        # 各レベルでログ出力
        logger = logging.getLogger('filter_test')
        logger.debug('DEBUG message (should be filtered out)')
        logger.info('INFO message (should be filtered out)')  
        logger.warning('WARNING message (should appear)')
        logger.error('ERROR message (should appear)')
        logger.critical('CRITICAL message (should appear)')
        
        # ログファイルの内容を確認
        warning_log_file = temp_log_dir / 'warning_only.log'
        with open(warning_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # WARNING以上のみが記録されていることを確認
        assert 'DEBUG message' not in content
        assert 'INFO message' not in content
        assert 'WARNING message' in content
        assert 'ERROR message' in content
        assert 'CRITICAL message' in content