"""
週次メトリクス計算サービス

データ層とプレゼンテーション層の間でメトリクス計算を行うビジネス層サービス
"""
import logging
from typing import List, Dict, Any
import pandas as pd

from ..data_layer.database_manager import DatabaseManager, DatabaseError
from .aggregator import ProductivityAggregator
from .timezone_handler import TimezoneHandler

logger = logging.getLogger(__name__)


class MetricsServiceError(Exception):
    """メトリクスサービス関連のエラー"""
    pass


class MetricsService:
    """週次メトリクス計算サービス
    
    データベースからプルリクエストデータを取得し、
    週次生産性メトリクスを計算するビジネスロジックを担当します。
    """
    
    def __init__(self, db_manager: DatabaseManager, timezone_handler: TimezoneHandler):
        """MetricsServiceを初期化
        
        Args:
            db_manager: データベース管理インスタンス
            timezone_handler: タイムゾーン処理インスタンス
        """
        self.db_manager = db_manager
        self.timezone_handler = timezone_handler
        self.aggregator = ProductivityAggregator(timezone_handler)
    
    def get_weekly_metrics(self) -> pd.DataFrame:
        """週次メトリクスデータを計算して取得
        
        データベースからプルリクエストデータを取得し、
        ProductivityVisualizerで使用可能な形式の週次メトリクスを計算して返します。
        
        Returns:
            pandas.DataFrame: 週次メトリクスのDataFrame
                必要な列: week_start, week_end, pr_count, unique_authors, productivity
        
        Raises:
            MetricsServiceError: データ取得またはメトリクス計算に失敗した場合
        """
        try:
            # データベースからプルリクエストデータを取得
            pr_data = self.db_manager.get_merged_pull_requests()
            
            if not pr_data:
                # 空のDataFrameを返す
                logger.info("No pull request data found, returning empty DataFrame")
                return pd.DataFrame(columns=['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity'])
            
            # 週次メトリクスを計算
            weekly_metrics = self.aggregator.calculate_weekly_metrics(pr_data)
            
            logger.info(f"Calculated weekly metrics for {len(weekly_metrics)} weeks")
            return weekly_metrics
            
        except DatabaseError as e:
            error_msg = f"Database error while retrieving pull request data: {e}"
            logger.error(error_msg)
            raise MetricsServiceError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error while calculating weekly metrics: {e}"
            logger.error(error_msg)
            raise MetricsServiceError(error_msg) from e
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """メトリクスの概要情報を取得
        
        週次メトリクスの基本的な統計情報を計算して返します。
        
        Returns:
            Dict[str, Any]: メトリクス概要
                - total_weeks: 対象週数
                - total_prs: 総プルリクエスト数
                - average_productivity: 平均生産性
                - max_productivity: 最大生産性
                - min_productivity: 最小生産性
        
        Raises:
            MetricsServiceError: メトリクス計算に失敗した場合
        """
        try:
            weekly_metrics = self.get_weekly_metrics()
            
            if weekly_metrics.empty:
                return {
                    'total_weeks': 0,
                    'total_prs': 0,
                    'average_productivity': 0.0,
                    'max_productivity': 0.0,
                    'min_productivity': 0.0
                }
            
            summary = {
                'total_weeks': len(weekly_metrics),
                'total_prs': int(weekly_metrics['pr_count'].sum()),
                'average_productivity': float(weekly_metrics['productivity'].mean()),
                'max_productivity': float(weekly_metrics['productivity'].max()),
                'min_productivity': float(weekly_metrics['productivity'].min())
            }
            
            logger.info(f"Generated metrics summary: {summary}")
            return summary
            
        except Exception as e:
            error_msg = f"Failed to generate metrics summary: {e}"
            logger.error(error_msg)
            raise MetricsServiceError(error_msg) from e
    
    def get_repository_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        リポジトリごとの統計情報を取得
        
        Returns:
            リポジトリ名をキーとする統計情報の辞書
            
        Raises:
            MetricsServiceError: データ取得エラー時
        """
        try:
            with self.db_manager.get_session() as session:
                # リポジトリごとのPR数と貢献者数を集計（N+1問題を解消）
                from sqlalchemy import func, distinct
                from ..data_layer.models import PullRequest
                
                # 単一のクエリですべてのリポジトリの統計を取得
                repo_stats_query = (
                    session.query(
                        PullRequest.repo_name,
                        func.count(PullRequest.id).label("pr_count"),
                        func.count(distinct(PullRequest.author)).label("unique_authors")
                    )
                    .group_by(PullRequest.repo_name)
                    .all()
                )

                repo_stats = {
                    repo_name: {"pr_count": pr_count, "unique_authors": unique_authors}
                    for repo_name, pr_count, unique_authors in repo_stats_query
                }
                
                return repo_stats
                
        except Exception as e:
            error_msg = f"Failed to get repository stats: {e}"
            logger.error(error_msg)
            raise MetricsServiceError(error_msg) from e