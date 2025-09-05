#!/usr/bin/env python3
"""
GitHub生産性メトリクス可視化ツール - エントリーポイント
依存関係注入とアプリケーション初期化を担当
"""
import os
import sys
import logging
from pathlib import Path
from typing import NamedTuple, Dict, Any
from dataclasses import dataclass

# 依存関係のインポート
from src.business_layer.config_loader import ConfigLoader
from src.business_layer.timezone_handler import TimezoneHandler
from src.business_layer.aggregator import ProductivityAggregator
from src.business_layer.sync_manager import SyncManager
from src.business_layer.metrics_service import MetricsService
from src.data_layer.github_client import GitHubClient
from src.data_layer.database_manager import DatabaseManager
from src.presentation_layer.visualizer import ProductivityVisualizer
from src.presentation_layer.cli import cli

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppComponents(NamedTuple):
    """アプリケーションのコアコンポーネント"""
    timezone_handler: TimezoneHandler
    github_client: GitHubClient
    db_manager: DatabaseManager
    aggregator: ProductivityAggregator
    config: Dict[str, Any]


class AppServices(NamedTuple):
    """アプリケーションのサービス層"""
    sync_manager: SyncManager
    metrics_service: MetricsService
    visualizer: ProductivityVisualizer


def load_and_validate_config() -> Dict[str, Any]:
    """設定ファイルの読み込みと検証
    
    Returns:
        Dict[str, Any]: 検証済み設定データ
        
    Raises:
        Exception: 設定読み込みまたは検証エラー
    """
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config('config.yaml')
        
        # GitHub APIトークンの環境変数からの取得
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise Exception(
                "GitHub APIトークンが設定されていません。\n"
                "環境変数 GITHUB_TOKEN を設定してください。"
            )
        
        # 設定にトークンを注入
        config['github']['api_token'] = github_token
        
        logger.info("Configuration loaded successfully")
        return config
        
    except Exception as e:
        logger.error(f"Configuration loading failed: {e}")
        raise


def create_app_components() -> AppComponents:
    """アプリケーションのコアコンポーネントを作成
    
    Returns:
        AppComponents: 初期化済みコンポーネント群
        
    Raises:
        Exception: コンポーネント初期化エラー
    """
    try:
        # 設定読み込み
        config = load_and_validate_config()
        
        # コアコンポーネントの初期化
        timezone_handler = TimezoneHandler(
            config.get('application', {}).get('timezone', 'Asia/Tokyo')
        )
        
        github_client = GitHubClient(
            token=config['github']['api_token'],
            base_url=config['github'].get('api_base_url', 'https://api.github.com')
        )
        
        # データベース設定とディレクトリ作成
        db_config = config.get('database', {})
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        db_path = data_dir / f"{db_config.get('name', 'gminor_db')}.sqlite"
        db_manager = DatabaseManager(str(db_path))
        
        # データベース初期化
        db_manager.initialize_database()
        
        # アグリゲータ初期化
        aggregator = ProductivityAggregator(timezone_handler)
        
        logger.info("Core components initialized successfully")
        return AppComponents(
            timezone_handler=timezone_handler,
            github_client=github_client,
            db_manager=db_manager,
            aggregator=aggregator,
            config=config
        )
        
    except Exception as e:
        logger.error(f"Component initialization failed: {e}")
        raise


def create_services(components: AppComponents) -> AppServices:
    """アプリケーションのサービス層を作成
    
    Args:
        components: 初期化済みコアコンポーネント
        
    Returns:
        AppServices: 初期化済みサービス群
        
    Raises:
        Exception: サービス初期化エラー
    """
    try:
        # サービス層の初期化（依存関係注入）
        sync_manager = SyncManager(
            components.github_client,
            components.db_manager,
            components.aggregator
        )
        
        metrics_service = MetricsService(
            components.db_manager,
            components.timezone_handler
        )
        
        visualizer = ProductivityVisualizer(components.timezone_handler)
        
        logger.info("Services initialized successfully")
        return AppServices(
            sync_manager=sync_manager,
            metrics_service=metrics_service,
            visualizer=visualizer
        )
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise


def setup_error_handling():
    """アプリケーション全体のエラーハンドリングを設定"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+Cによる中断は通常終了として扱う
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error(
            "Uncaught exception", 
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        print(f"予期しないエラーが発生しました: {exc_value}", file=sys.stderr)
    
    sys.excepthook = handle_exception


def main():
    """メイン関数 - アプリケーションのエントリーポイント"""
    try:
        # エラーハンドリング設定
        setup_error_handling()
        
        # アプリケーション初期化
        logger.info("Starting gminor application")
        
        # コンポーネントとサービスの初期化（依存関係注入）
        components = create_app_components()
        services = create_services(components)
        
        # CLI実行
        cli()
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        print(f"アプリケーション起動エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()