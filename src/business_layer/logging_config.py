"""ログ設定管理モジュール

アプリケーション全体のログ設定を管理し、一元的なログ設定機能を提供します。
"""
import logging
import logging.handlers
import re
from pathlib import Path
from typing import Dict, Any, Optional


class LoggingConfig:
    """ログ設定クラス
    
    設定データからログ関連の設定を管理し、適切なログ設定を提供します。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """LoggingConfigを初期化
        
        Args:
            config: ログ設定辞書
        """
        self.level = config.get('level', 'INFO')
        self.file_path = config.get('file', './logs/app.log')
        self.format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.max_file_size = config.get('max_file_size', '10MB')
        self.backup_count = config.get('backup_count', 5)
    
    def get_log_level(self) -> int:
        """ログレベル文字列をloggingモジュールの定数に変換
        
        Returns:
            int: ログレベル定数
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(self.level.upper(), logging.INFO)
    
    def get_max_bytes(self) -> int:
        """ファイルサイズ文字列をバイト数に変換
        
        Returns:
            int: 最大ファイルサイズ（バイト）
        """
        try:
            # サイズ文字列を解析 (例: "10MB", "5GB", "100KB")
            match = re.match(r'(\d+)(KB|MB|GB)', self.max_file_size.upper())
            if not match:
                return 10 * 1024 * 1024  # デフォルト10MB
            
            size, unit = match.groups()
            size = int(size)
            
            multipliers = {
                'KB': 1024,
                'MB': 1024 * 1024,
                'GB': 1024 * 1024 * 1024
            }
            
            return size * multipliers[unit]
            
        except (ValueError, AttributeError):
            return 10 * 1024 * 1024  # デフォルト10MB


def setup_logging(config: Dict[str, Any]) -> None:
    """アプリケーション全体のログを設定
    
    設定ファイルに基づいてアプリケーション全体のログ設定を行います。
    ファイル出力、ローテーション、フォーマット等を設定します。
    
    Args:
        config: アプリケーション設定辞書
    """
    # ログ設定を取得（存在しない場合はデフォルト）
    logging_config_dict = config.get('logging', {})
    logging_config = LoggingConfig(logging_config_dict)
    
    # 既存のログハンドラーをクリア
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # ログレベル設定
    root_logger.setLevel(logging_config.get_log_level())
    
    # フォーマッター作成
    formatter = logging.Formatter(logging_config.format)
    
    # コンソールハンドラー追加
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging_config.get_log_level())
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー追加
    log_file_path = Path(logging_config.file_path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ローテーティングファイルハンドラー設定
    file_handler = logging.handlers.RotatingFileHandler(
        filename=logging_config.file_path,
        maxBytes=logging_config.get_max_bytes(),
        backupCount=logging_config.backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging_config.get_log_level())
    root_logger.addHandler(file_handler)
    
    # 設定完了ログ
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={logging_config.level}, file={logging_config.file_path}")