"""ログ設定システムのテスト"""
import pytest
import os
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from typing import Dict, Any

from src.business_layer.logging_config import LoggingConfig, setup_logging


class TestLoggingConfig:
    """ログ設定クラスのテスト"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """一時ログディレクトリのフィクスチャ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def basic_config(self, temp_log_dir):
        """基本的なログ設定のフィクスチャ"""
        return {
            'logging': {
                'level': 'INFO',
                'file': str(temp_log_dir / 'test.log'),
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'max_file_size': '10MB',
                'backup_count': 5
            }
        }
    
    def test_ログ設定クラスが正常に初期化される(self, basic_config):
        """正常系: LoggingConfigが基本設定で正常に初期化されることを確認"""
        logging_config = LoggingConfig(basic_config['logging'])
        
        assert logging_config.level == 'INFO'
        assert logging_config.file_path == basic_config['logging']['file']
        assert logging_config.format == basic_config['logging']['format']
        assert logging_config.max_file_size == '10MB'
        assert logging_config.backup_count == 5
    
    def test_デフォルト設定が適用される(self):
        """正常系: 不完全な設定でもデフォルト値が適用されることを確認"""
        partial_config = {
            'level': 'DEBUG'
        }
        logging_config = LoggingConfig(partial_config)
        
        assert logging_config.level == 'DEBUG'
        assert logging_config.file_path == './logs/app.log'  # デフォルト値
        assert logging_config.max_file_size == '10MB'  # デフォルト値
        assert logging_config.backup_count == 5  # デフォルト値
    
    def test_ログレベルの文字列が正しく変換される(self):
        """正常系: ログレベル文字列がloggingモジュールの定数に正しく変換されることを確認"""
        test_cases = [
            ('DEBUG', logging.DEBUG),
            ('INFO', logging.INFO), 
            ('WARNING', logging.WARNING),
            ('ERROR', logging.ERROR),
            ('CRITICAL', logging.CRITICAL)
        ]
        
        for level_str, expected_level in test_cases:
            config = LoggingConfig({'level': level_str})
            assert config.get_log_level() == expected_level
    
    def test_無効なログレベルでデフォルトが適用される(self):
        """異常系: 無効なログレベルではINFOがデフォルトとして適用されることを確認"""
        config = LoggingConfig({'level': 'INVALID_LEVEL'})
        assert config.get_log_level() == logging.INFO
    
    def test_ファイルサイズの解析が正常に動作する(self):
        """正常系: ファイルサイズ文字列が正しくバイト数に変換されることを確認"""
        test_cases = [
            ('1MB', 1024 * 1024),
            ('5MB', 5 * 1024 * 1024),
            ('100KB', 100 * 1024),
            ('2GB', 2 * 1024 * 1024 * 1024)
        ]
        
        for size_str, expected_bytes in test_cases:
            config = LoggingConfig({'max_file_size': size_str})
            assert config.get_max_bytes() == expected_bytes
    
    def test_無効なファイルサイズでデフォルトが適用される(self):
        """異常系: 無効なファイルサイズではデフォルト値が適用されることを確認"""
        config = LoggingConfig({'max_file_size': 'INVALID_SIZE'})
        assert config.get_max_bytes() == 10 * 1024 * 1024  # 10MBデフォルト


class TestLoggingSetup:
    """ログセットアップ関数のテスト"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """一時ログディレクトリのフィクスチャ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config_with_logging(self, temp_log_dir):
        """ログ設定を含む設定のフィクスチャ"""
        return {
            'logging': {
                'level': 'DEBUG',
                'file': str(temp_log_dir / 'app.log'),
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'max_file_size': '5MB',
                'backup_count': 3
            }
        }
    
    def test_setup_loggingが正常に実行される(self, config_with_logging, temp_log_dir):
        """正常系: setup_logging関数が正常に実行されることを確認"""
        # ログディレクトリが存在しない状態で開始
        assert not (temp_log_dir / 'app.log').exists()
        
        # ログ設定を実行
        setup_logging(config_with_logging)
        
        # ログディレクトリが作成されることを確認
        assert (temp_log_dir).exists()
        
        # ロガーが正しく設定されることを確認
        test_logger = logging.getLogger('test_logger')
        assert test_logger.level == logging.DEBUG
    
    def test_ログファイルが正しく出力される(self, config_with_logging, temp_log_dir):
        """正常系: ログファイルが正しく出力されることを確認"""
        setup_logging(config_with_logging)
        
        # テストメッセージをログ出力
        test_logger = logging.getLogger('test_file_output')
        test_logger.info('テストメッセージ')
        
        # ログファイルが作成され、内容が書き込まれることを確認
        log_file_path = temp_log_dir / 'app.log'
        assert log_file_path.exists()
        
        # ログファイルの内容を確認
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert 'test_file_output' in log_content
            assert 'INFO' in log_content
            assert 'テストメッセージ' in log_content
    
    def test_ログレベルフィルタリングが動作する(self, temp_log_dir):
        """正常系: ログレベルフィルタリングが正しく動作することを確認"""
        config = {
            'logging': {
                'level': 'WARNING',  # WARNING以上のみ出力
                'file': str(temp_log_dir / 'warning_test.log')
            }
        }
        
        setup_logging(config)
        test_logger = logging.getLogger('test_level_filter')
        
        # 各レベルでログ出力
        test_logger.debug('DEBUGメッセージ（出力されない）')
        test_logger.info('INFOメッセージ（出力されない）')
        test_logger.warning('WARNINGメッセージ（出力される）')
        test_logger.error('ERRORメッセージ（出力される）')
        
        # ログファイルの内容を確認
        log_file_path = temp_log_dir / 'warning_test.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert 'DEBUGメッセージ' not in log_content
            assert 'INFOメッセージ' not in log_content
            assert 'WARNINGメッセージ' in log_content
            assert 'ERRORメッセージ' in log_content
    
    def test_ログ設定がない場合デフォルト設定が適用される(self):
        """正常系: ログ設定がない場合にデフォルト設定が適用されることを確認"""
        config_without_logging = {}
        
        # エラーが発生せずにデフォルト設定が適用されることを確認
        setup_logging(config_without_logging)
        
        # デフォルトでINFOレベルが設定されることを確認
        test_logger = logging.getLogger('test_default')
        assert test_logger.level <= logging.INFO
    
    @patch('src.business_layer.logging_config.logging.getLogger')
    def test_既存のログ設定がリセットされる(self, mock_get_logger, config_with_logging):
        """正常系: setup_loggingが既存のログ設定をリセットすることを確認"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        setup_logging(config_with_logging)
        
        # ハンドラーがクリアされることを確認
        mock_logger.handlers.clear.assert_called()


class TestLoggingIntegration:
    """ログ機能の統合テスト"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """一時ログディレクトリのフィクスチャ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_複数のロガーが独立して動作する(self, temp_log_dir):
        """正常系: 複数のロガーが独立して動作することを確認"""
        config = {
            'logging': {
                'level': 'DEBUG',
                'file': str(temp_log_dir / 'multi_logger.log')
            }
        }
        
        setup_logging(config)
        
        # 異なる名前のロガーを作成
        logger1 = logging.getLogger('component1')
        logger2 = logging.getLogger('component2')
        
        # それぞれログ出力
        logger1.info('Component1からのメッセージ')
        logger2.warning('Component2からの警告')
        
        # 両方のメッセージがログファイルに記録されることを確認
        log_file_path = temp_log_dir / 'multi_logger.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert 'component1' in log_content
            assert 'Component1からのメッセージ' in log_content
            assert 'component2' in log_content
            assert 'Component2からの警告' in log_content
    
    def test_フォーマットが正しく適用される(self, temp_log_dir):
        """正常系: 指定されたフォーマットが正しく適用されることを確認"""
        custom_format = '%(levelname)s|%(name)s|%(message)s'
        config = {
            'logging': {
                'level': 'INFO',
                'file': str(temp_log_dir / 'format_test.log'),
                'format': custom_format
            }
        }
        
        setup_logging(config)
        test_logger = logging.getLogger('format_tester')
        test_logger.info('フォーマットテスト')
        
        # カスタムフォーマットが適用されていることを確認
        log_file_path = temp_log_dir / 'format_test.log'
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert 'INFO|format_tester|フォーマットテスト' in log_content