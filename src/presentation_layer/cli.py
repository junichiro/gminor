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


def create_services_from_components(
    timezone_handler: TimezoneHandler,
    github_client: GitHubClient, 
    db_manager: DatabaseManager,
    aggregator: ProductivityAggregator
) -> Dict[str, Any]:
    """コンポーネントからサービス層を作成する（CLIの独立実行用）
    
    Args:
        timezone_handler: タイムゾーンハンドラー
        github_client: GitHubクライアント
        db_manager: データベースマネージャー
        aggregator: プロダクティビティアグリゲーター
        
    Returns:
        Dict[str, Any]: 作成されたサービス群
        
    Raises:
        click.ClickException: サービス作成エラー
    """
    try:
        sync_manager = SyncManager(github_client, db_manager, aggregator)
        metrics_service = MetricsService(db_manager, timezone_handler)
        visualizer = ProductivityVisualizer(timezone_handler)
        
        return {
            'sync_manager': sync_manager,
            'metrics_service': metrics_service,
            'visualizer': visualizer
        }
        
    except Exception as e:
        raise click.ClickException(f"サービスの初期化に失敗しました: {str(e)}")


@click.group()
@click.pass_context
def cli(ctx):
    """GitHub生産性メトリクス可視化ツール"""
    # コンテキストオブジェクトが存在しない場合は独立実行モード
    if ctx.obj is None:
        ctx.ensure_object(dict)
        # 独立実行時のみコンポーネントを作成
        config = load_config_and_validate()
        components = create_components(config)
        services = create_services_from_components(*components)
        ctx.obj = {
            'components': components,
            'services': services,
            'config': config
        }


@cli.command()
@click.option('--days', default=180, help='取得期間（日）', type=int)
@click.pass_context
def init(ctx, days: int):
    """初回データ取得"""
    click.echo("初期データ同期を開始しています...")
    
    # コンテキストから依存関係を取得
    config = ctx.obj['config']
    timezone_handler, github_client, db_manager, aggregator = ctx.obj['components']
    services = ctx.obj['services']
    
    # リポジトリ設定の確認
    repositories = config['github'].get('repositories', [])
    if not repositories:
        raise click.ClickException(
            "設定ファイルにリポジトリが定義されていません。\n"
            "config.yaml の github.repositories に対象リポジトリを追加してください。"
        )
    
    try:
        # 注入されたSyncManagerを使用
        sync_manager = services['sync_manager']
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
@click.pass_context
def update(ctx):
    """差分データ同期を実行"""
    click.echo("🔄 差分データ同期を開始しています...")
    
    # コンテキストから依存関係を取得
    config = ctx.obj['config']
    timezone_handler, github_client, db_manager, aggregator = ctx.obj['components']
    services = ctx.obj['services']
    
    # リポジトリ設定の確認
    repositories = config['github'].get('repositories', [])
    if not repositories:
        raise click.ClickException(
            "設定ファイルにリポジトリが定義されていません。\n"
            "config.yaml の github.repositories に対象リポジトリを追加してください。"
        )
    
    try:
        # 注入されたSyncManagerを使用して差分同期実行
        sync_manager = services['sync_manager']
        result = sync_manager.update_sync(repositories)
        
        # 結果の表示
        _display_sync_result(result)
        
    except Exception as e:
        raise click.ClickException(f"差分同期処理中にエラーが発生しました: {str(e)}")
    finally:
        # リソースのクリーンアップ
        db_manager.close()


@cli.command()
@click.pass_context
def visualize(ctx):
    """可視化のみ実行"""
    click.echo("📊 グラフ生成を開始しています...")
    
    # コンテキストから依存関係を取得
    config = ctx.obj['config']
    timezone_handler, github_client, db_manager, aggregator = ctx.obj['components']
    services = ctx.obj['services']
    
    # データベースファイルの存在確認
    db_config = config.get('database', {})
    db_path = f"data/{db_config.get('name', 'gminor_db')}.sqlite"
    if not Path(db_path).exists():
        raise click.ClickException(
            f"データベースファイルが見つかりません: {db_path}\n"
            "まず 'init' コマンドを実行してデータを取得してください。"
        )
    
    try:
        # 注入されたサービスを使用
        metrics_service = services['metrics_service']
        visualizer = services['visualizer']
        
        # ビジネス層から週次メトリクスを取得
        weekly_data = metrics_service.get_weekly_metrics()
        
        if weekly_data.empty:
            click.echo("📭 データがありません。まず 'init' コマンドを実行してデータを取得してください。")
            return
        
        click.echo(f"📈 {len(weekly_data)}週分のデータを可視化します...")
        
        # 4週移動平均を計算して追加
        moving_average_window = 4  # デフォルトのウィンドウサイズ
        weekly_data['moving_average'] = aggregator.calculate_moving_average(weekly_data, window=moving_average_window)
        
        # グラフ生成（ウィンドウサイズを渡す）
        html_content = visualizer.create_productivity_chart(weekly_data, moving_average_window=moving_average_window)
        
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