"""
週次集計ロジックを担当するモジュール
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
from datetime import datetime

from .timezone_handler import TimezoneHandler


class ProductivityAggregator:
    """生産性メトリクスの週次集計を担当するクラス"""
    
    REQUIRED_COLUMNS = ['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity']
    
    def __init__(self, timezone_handler: TimezoneHandler) -> None:
        """
        ProductivityAggregatorを初期化
        
        Args:
            timezone_handler: タイムゾーン処理を担当するハンドラー
        """
        self.timezone_handler = timezone_handler
    
    def calculate_weekly_metrics(self, prs: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        PRデータから週次メトリクスを計算
        
        Args:
            prs: PRデータのリスト。各PRは以下のキーを含む辞書:
                - merged_at: マージされた日時 (datetime)
                - author: 作成者名 (str)
                - 他のフィールドは任意
            
        Returns:
            週次メトリクスを含むDataFrame。列:
                - week_start: 週開始日時
                - week_end: 週終了日時  
                - pr_count: PR数
                - unique_authors: ユニークな作成者数
                - productivity: 生産性（PR数/作成者数）
        """
        if not prs:
            return self._create_empty_dataframe()
        
        # PRデータの前処理
        processed_data = self._preprocess_pr_data(prs)
        
        # 週次集計の実行
        return self._aggregate_by_week(processed_data)
    
    def _create_empty_dataframe(self) -> pd.DataFrame:
        """空のDataFrameを作成"""
        return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
    
    def _preprocess_pr_data(self, prs: List[Dict[str, Any]]) -> pd.DataFrame:
        """PRデータを前処理してDataFrameを作成"""
        df = pd.DataFrame(prs)
        
        # merged_atを datetime型に変換してソート
        df['merged_at'] = pd.to_datetime(df['merged_at'])
        df = df.sort_values('merged_at')
        
        # 週境界情報を追加
        df = self._add_week_boundaries(df)
        
        return df
    
    def _add_week_boundaries(self, df: pd.DataFrame) -> pd.DataFrame:
        """週境界情報をDataFrameに追加"""
        df['week_boundaries'] = df['merged_at'].apply(
            lambda dt: self.timezone_handler.get_week_boundaries(dt)
        )
        df['week_start'] = df['week_boundaries'].apply(lambda x: x[0])
        df['week_end'] = df['week_boundaries'].apply(lambda x: x[1])
        
        return df
    
    def _aggregate_by_week(self, df: pd.DataFrame) -> pd.DataFrame:
        """週次でデータを集計"""
        weekly_groups = df.groupby(['week_start', 'week_end'])
        
        results = []
        for (week_start, week_end), group in weekly_groups:
            metrics = self._calculate_group_metrics(group, week_start, week_end)
            results.append(metrics)
        
        return pd.DataFrame(results, columns=self.REQUIRED_COLUMNS)
    
    def _calculate_group_metrics(
        self, 
        group: pd.DataFrame, 
        week_start: datetime, 
        week_end: datetime
    ) -> Dict[str, Any]:
        """グループのメトリクスを計算"""
        pr_count = len(group)
        unique_authors = group['author'].nunique()
        productivity = self._calculate_productivity(pr_count, unique_authors)
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'pr_count': pr_count,
            'unique_authors': unique_authors,
            'productivity': productivity
        }
    
    def _calculate_productivity(self, pr_count: int, unique_authors: int) -> float:
        """生産性を計算（ゼロ除算を避ける）"""
        return pr_count / unique_authors if unique_authors > 0 else 0.0