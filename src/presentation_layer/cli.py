"""
CLI コマンド実装（init・visualize）
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import click
import pandas as pd

from ..business_layer.config_loader import ConfigLoader
from ..business_layer.sync_manager import SyncManager
from ..business_layer.timezone_handler import TimezoneHandler
from ..business_layer.aggregator import ProductivityAggregator
from ..business_layer.metrics_service import MetricsService, MetricsServiceError
from ..data_layer.github_client import GitHubClient
from ..data_layer.database_manager import DatabaseManager
from .visualizer import ProductivityVisualizer


def load_config_and_validate() -> Dict[str, Any]:
    """設定ファイルの読み込みと検証を行う
    
    Returns:
        Dict[str, Any]: 読み込まれた設定
        
    Raises:
        click.ClickException: 設定読み込みエラーまたは検証エラー
    """
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config('config.yaml')
        
        # GitHub APIトークンの環境変数からの取得
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise click.ClickException(
                "GitHub APIトークンが設定されていません。\n"
                "環境変数 GITHUB_TOKEN を設定してください。"
            )
        
        # 設定にトークンを追加
        config['github']['api_token'] = github_token
        
        return config
        
    except Exception as e:
        raise click.ClickException(f"設定ファイルの読み込みに失敗しました: {str(e)}")


def create_components(config: Dict[str, Any]) -> tuple[TimezoneHandler, GitHubClient, DatabaseManager, ProductivityAggregator]:
    """必要なコンポーネントを作成する
    
    Args:
        config: アプリケーション設定
        
    Returns:
        tuple: 作成されたコンポーネント（timezone_handler, github_client, db_manager, aggregator）
        
    Raises:
        click.ClickException: コンポーネント作成エラー
    """
    try:
        # 必要なコンポーネントの初期化
        timezone_handler = TimezoneHandler(config.get('application', {}).get('timezone', 'Asia/Tokyo'))
        
        github_client = GitHubClient(
            token=config['github']['api_token'],
            base_url=config['github'].get('api_base_url', 'https://api.github.com')
        )
        
        # データベース設定からSQLiteパスを構築
        db_config = config.get('database', {})
        db_path = f"data/{db_config.get('name', 'gminor_db')}.sqlite"
        
        # データディレクトリの作成
        Path("data").mkdir(exist_ok=True)
        
        db_manager = DatabaseManager(db_path)
        # データベース初期化（テーブル作成）
        db_manager.initialize_database()
        
        aggregator = ProductivityAggregator(timezone_handler)
        
        return timezone_handler, github_client, db_manager, aggregator
        
    except Exception as e:
        raise click.ClickException(f"コンポーネントの初期化に失敗しました: {str(e)}")


@click.group()
def cli():
    """GitHub生産性メトリクス可視化ツール"""
    pass


@cli.command()
@click.option('--days', default=180, help='取得期間（日）', type=int)
def init(days: int):
    """初回データ取得"""
    click.echo("初期データ同期を開始しています...")
    
    # 設定読み込みとコンポーネント初期化
    config = load_config_and_validate()
    timezone_handler, github_client, db_manager, aggregator = create_components(config)
    
    # リポジトリ設定の確認
    repositories = config['github'].get('repositories', [])
    if not repositories:
        raise click.ClickException(
            "設定ファイルにリポジトリが定義されていません。\n"
            "config.yaml の github.repositories に対象リポジトリを追加してください。"
        )
    
    try:
        # SyncManagerによる初期データ同期
        sync_manager = SyncManager(github_client, db_manager, aggregator)
        result = sync_manager.initial_sync(repositories, days_back=days, progress=True)
        
        # 結果の表示
        _display_sync_result(result)
        
    except Exception as e:
        db_manager.close()
        raise click.ClickException(f"同期処理中にエラーが発生しました: {str(e)}")
    finally:
        # リソースのクリーンアップ
        db_manager.close()


def _display_sync_result(result: Dict[str, Any]) -> None:
    """同期結果を表示する
    
    Args:
        result: SyncManagerからの結果辞書
    """
    if result['status'] == 'success':
        click.echo("✅ データ同期が完了しました！")
        click.echo(f"📊 処理したリポジトリ数: {len(result['processed_repositories'])}")
        click.echo(f"📋 取得したPR数: {result['total_prs_fetched']}")
        click.echo(f"⏱️  実行時間: {result['sync_duration_seconds']:.1f}秒")
    
    elif result['status'] == 'partial_success':
        click.echo("⚠️  データ同期が部分的に完了しました")
        click.echo(f"✅ 成功したリポジトリ数: {len(result['processed_repositories'])}")
        click.echo(f"❌ 失敗したリポジトリ数: {result.get('failed_count', 0)}")
        click.echo(f"📋 取得したPR数: {result['total_prs_fetched']}")
        click.echo(f"⏱️  実行時間: {result['sync_duration_seconds']:.1f}秒")
        
        if 'failed_repositories' in result:
            click.echo("\n失敗したリポジトリ:")
            for repo in result['failed_repositories']:
                click.echo(f"  - {repo}")
    
    else:
        error_msg = result.get('error', 'Unknown error')
        raise click.ClickException(f"同期に失敗しました: {error_msg}")


@cli.command()
def visualize():
    """可視化のみ実行"""
    click.echo("📊 グラフ生成を開始しています...")
    
    # 設定読み込み（GitHub APIトークンは不要なので簡易版）
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config('config.yaml')
    except Exception as e:
        raise click.ClickException(f"設定ファイルの読み込みに失敗しました: {str(e)}")
    
    # 必要なコンポーネントの初期化
    try:
        timezone_handler = TimezoneHandler(config.get('application', {}).get('timezone', 'Asia/Tokyo'))
        
        # データベース設定からSQLiteパスを構築
        db_config = config.get('database', {})
        db_path = f"data/{db_config.get('name', 'gminor_db')}.sqlite"
        
        # データベースファイルの存在確認
        if not Path(db_path).exists():
            raise click.ClickException(
                f"データベースファイルが見つかりません: {db_path}\n"
                "まず 'init' コマンドを実行してデータを取得してください。"
            )
        
        db_manager = DatabaseManager(db_path)
        visualizer = ProductivityVisualizer(timezone_handler)
        metrics_service = MetricsService(db_manager, timezone_handler)
        
    except Exception as e:
        raise click.ClickException(f"コンポーネントの初期化に失敗しました: {str(e)}")
    
    try:
        # ビジネス層から週次メトリクスを取得
        weekly_data = metrics_service.get_weekly_metrics()
        
        if weekly_data.empty:
            click.echo("📭 データがありません。まず 'init' コマンドを実行してデータを取得してください。")
            return
        
        click.echo(f"📈 {len(weekly_data)}週分のデータを可視化します...")
        
        # グラフ生成
        html_content = visualizer.create_productivity_chart(weekly_data)
        
        # 出力ディレクトリとファイルパスの準備
        output_config = config.get('application', {}).get('output', {})
        output_dir = Path(output_config.get('directory', 'output'))
        output_filename = output_config.get('filename', 'productivity_chart.html')
        
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / output_filename
        
        # HTMLファイルとして保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        click.echo(f"✅ グラフが正常に生成されました: {output_path}")
        click.echo(f"🌐 ブラウザで開いてご確認ください。")
        
    except MetricsServiceError as e:
        raise click.ClickException(f"メトリクス計算中にエラーが発生しました: {str(e)}")
    except FileNotFoundError as e:
        raise click.ClickException(f"ファイル操作エラー: {str(e)}")
    except PermissionError as e:
        raise click.ClickException(f"ファイル書き込み権限エラー: {str(e)}")
    except Exception as e:
        raise click.ClickException(f"予期しないエラーが発生しました: {str(e)}")
    finally:
        # リソースのクリーンアップ
        db_manager.close()


if __name__ == '__main__':
    cli()