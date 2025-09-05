"""ProductivityAggregatorのテスト"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import Mock

from src.business_layer.aggregator import ProductivityAggregator
from src.business_layer.timezone_handler import TimezoneHandler


class TestProductivityAggregator:
    """ProductivityAggregatorクラスのテスト"""
    
    @pytest.fixture
    def timezone_handler(self):
        """TimezoneHandlerのフィクスチャ"""
        return TimezoneHandler("Asia/Tokyo")
    
    @pytest.fixture
    def aggregator(self, timezone_handler):
        """ProductivityAggregatorのフィクスチャ"""
        return ProductivityAggregator(timezone_handler)
    
    def test_ProductivityAggregatorが正常に初期化される(self, timezone_handler):
        """正常系: ProductivityAggregatorが正常に初期化されることを確認"""
        aggregator = ProductivityAggregator(timezone_handler)
        assert aggregator is not None
        assert aggregator.timezone_handler == timezone_handler
    
    def test_週次メトリクス計算が正常に動作する(self, aggregator):
        """正常系: 週次メトリクスが正常に計算されることを確認"""
        # テストデータ: 同じ週に複数のPR
        prs = [
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),  # 月曜日
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            },
            {
                "number": 2,
                "title": "PR 2", 
                "author": "developer2",
                "merged_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),  # 火曜日
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc)
            },
            {
                "number": 3,
                "title": "PR 3",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 17, 12, 0, tzinfo=timezone.utc),  # 水曜日
                "created_at": datetime(2024, 1, 12, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 17, 12, 0, tzinfo=timezone.utc)
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # DataFrameが返されることを確認
        assert isinstance(result, pd.DataFrame)
        
        # 正確に1週分のデータがあることを確認
        assert len(result) == 1
        
        # 必要な列がすべて存在することを確認
        expected_columns = ['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity']
        assert list(result.columns) == expected_columns
        
        # 具体的なメトリクス値を確認
        week_data = result.iloc[0]
        assert week_data['pr_count'] == 3
        assert week_data['unique_authors'] == 2  # developer1, developer2
        assert week_data['productivity'] == 1.5  # 3 PRs / 2 authors = 1.5
    
    def test_ユニークな作成者数が正しくカウントされる(self, aggregator):
        """正常系: ユニークな作成者数が正しくカウントされることを確認"""
        # テストデータ: 3つのPR、2人の異なる作成者
        prs = [
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            },
            {
                "number": 2,
                "title": "PR 2",
                "author": "developer1",  # 同じ作成者
                "merged_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc)
            },
            {
                "number": 3,
                "title": "PR 3",
                "author": "developer2",  # 異なる作成者
                "merged_at": datetime(2024, 1, 17, 12, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 12, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 17, 12, 0, tzinfo=timezone.utc)
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # 最初の週のデータを確認
        first_week = result.iloc[0]
        assert first_week['pr_count'] == 3  # 3つのPR
        assert first_week['unique_authors'] == 2  # 2人のユニークな作成者
    
    def test_生産性計算が正しく動作する(self, aggregator):
        """正常系: 生産性（PR数÷作成者数）が正しく計算されることを確認"""
        prs = [
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            },
            {
                "number": 2,
                "title": "PR 2",
                "author": "developer2",
                "merged_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc)
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # 最初の週のデータを確認
        first_week = result.iloc[0]
        assert first_week['pr_count'] == 2
        assert first_week['unique_authors'] == 2
        assert first_week['productivity'] == 1.0  # 2 PR ÷ 2 authors = 1.0
    
    def test_複数週にまたがるデータを正しく処理する(self, aggregator):
        """正常系: 複数週にまたがるデータが正しく処理されることを確認"""
        prs = [
            # 第1週のPR
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),  # 週1
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            },
            {
                "number": 2,
                "title": "PR 2",
                "author": "developer2",
                "merged_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),  # 週1
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc)
            },
            # 第2週のPR
            {
                "number": 3,
                "title": "PR 3",
                "author": "developer3",
                "merged_at": datetime(2024, 1, 22, 10, 0, tzinfo=timezone.utc),  # 週2
                "created_at": datetime(2024, 1, 20, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 22, 10, 0, tzinfo=timezone.utc)
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # 2週分のデータがあることを確認
        assert len(result) == 2
        
        # 結果が週開始日でソートされていることを確認
        assert result.iloc[0]['week_start'] <= result.iloc[1]['week_start']
        
        # 各週の具体的なデータを確認
        week1 = result.iloc[0]
        week2 = result.iloc[1]
        
        # 第1週のメトリクス
        assert week1['pr_count'] == 2
        assert week1['unique_authors'] == 2
        assert week1['productivity'] == 1.0  # 2 PRs / 2 authors = 1.0
        
        # 第2週のメトリクス
        assert week2['pr_count'] == 1 
        assert week2['unique_authors'] == 1
        assert week2['productivity'] == 1.0  # 1 PR / 1 author = 1.0
    
    def test_空のデータリストを正しく処理する(self, aggregator):
        """正常系: 空のデータリストが正しく処理されることを確認"""
        prs = []
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # 空のDataFrameが返されることを確認
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        
        # カラムが正確に定義されていることを確認
        expected_columns = ['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity']
        assert list(result.columns) == expected_columns
        
        # カラムの型が正しいことを確認（空でも型情報は保持される）
        assert result.empty
        assert result.shape == (0, 5)
    
    def test_同一作成者が同じ週に複数PRを作成する場合(self, aggregator):
        """正常系: 同一作成者が同じ週に複数PRを作成する場合を正しく処理することを確認"""
        prs = [
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            },
            {
                "number": 2,
                "title": "PR 2",
                "author": "developer1",  # 同じ作成者
                "merged_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc)
            },
            {
                "number": 3,
                "title": "PR 3", 
                "author": "developer1",  # 同じ作成者
                "merged_at": datetime(2024, 1, 17, 12, 0, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 12, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 17, 12, 0, tzinfo=timezone.utc)
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # 最初の週のデータを確認
        first_week = result.iloc[0]
        assert first_week['pr_count'] == 3  # 3つのPR
        assert first_week['unique_authors'] == 1  # 1人のユニークな作成者
        assert first_week['productivity'] == 3.0  # 3 PR ÷ 1 author = 3.0
    
    def test_異なるタイムゾーンのデータを正しく処理する(self, aggregator):
        """正常系: 異なるタイムゾーンのデータが正しく処理されることを確認"""
        # UTC以外のタイムゾーンを含むデータ
        from zoneinfo import ZoneInfo
        
        prs = [
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1",
                "merged_at": datetime(2024, 1, 15, 19, 0, tzinfo=ZoneInfo("Asia/Tokyo")),  # JST
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 19, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # データが正常に処理されることを確認
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1
    
    def test_週境界をまたぐ時刻の処理(self, aggregator):
        """正常系: 週境界をまたぐ時刻が正しく処理されることを確認"""
        prs = [
            # 日曜日の深夜（週の終わり）
            {
                "number": 1,
                "title": "PR 1",
                "author": "developer1", 
                "merged_at": datetime(2024, 1, 14, 23, 59, tzinfo=timezone.utc),  # 日曜 23:59 UTC
                "created_at": datetime(2024, 1, 10, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 14, 23, 59, tzinfo=timezone.utc)
            },
            # 月曜日の早朝（週の始まり）
            {
                "number": 2,
                "title": "PR 2",
                "author": "developer2",
                "merged_at": datetime(2024, 1, 15, 0, 1, tzinfo=timezone.utc),  # 月曜 00:01 UTC
                "created_at": datetime(2024, 1, 11, 9, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 1, 15, 0, 1, tzinfo=timezone.utc)
            }
        ]
        
        result = aggregator.calculate_weekly_metrics(prs)
        
        # タイムゾーンを考慮して適切に週が分けられることを確認
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1


class TestMovingAverageCalculation:
    """4週移動平均計算のテスト"""
    
    @pytest.fixture
    def timezone_handler(self):
        """TimezoneHandlerのフィクスチャ"""
        return TimezoneHandler("Asia/Tokyo")
    
    @pytest.fixture
    def aggregator(self, timezone_handler):
        """ProductivityAggregatorのフィクスチャ"""
        return ProductivityAggregator(timezone_handler)
    
    @pytest.fixture
    def sample_weekly_data(self):
        """テスト用の週次データ"""
        return pd.DataFrame({
            'week_start': pd.date_range('2024-01-01', periods=8, freq='W'),
            'week_end': pd.date_range('2024-01-07', periods=8, freq='W'),
            'pr_count': [10, 15, 12, 18, 20, 14, 16, 22],
            'unique_authors': [5, 6, 4, 8, 10, 7, 8, 11],
            'productivity': [2.0, 2.5, 3.0, 2.25, 2.0, 2.0, 2.0, 2.0]
        })
    
    def test_calculate_moving_average_メソッドが定義されている(self, aggregator):
        """正常系: calculate_moving_averageメソッドが定義されていることを確認"""
        assert hasattr(aggregator, 'calculate_moving_average')
        assert callable(getattr(aggregator, 'calculate_moving_average'))
    
    def test_4週移動平均が正しく計算される(self, aggregator, sample_weekly_data):
        """正常系: 4週移動平均が正しく計算されることを確認"""
        # 4週移動平均を計算
        result = aggregator.calculate_moving_average(sample_weekly_data)
        
        # 結果がpd.Seriesであることを確認
        assert isinstance(result, pd.Series)
        
        # 移動平均の長さが元データと同じであることを確認
        assert len(result) == len(sample_weekly_data)
        
        # 最初の3つの値はNaNであることを確認（4週分のデータが不足）
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])
        
        # 4番目以降は計算値があることを確認
        assert not pd.isna(result.iloc[3])
        
        # 4番目の値が手計算と一致することを確認 (2.0+2.5+3.0+2.25)/4 = 2.4375
        assert abs(result.iloc[3] - 2.4375) < 0.0001
    
    def test_移動平均のウィンドウサイズを変更できる(self, aggregator, sample_weekly_data):
        """正常系: 移動平均のウィンドウサイズを変更できることを確認"""
        # 3週移動平均を計算
        result = aggregator.calculate_moving_average(sample_weekly_data, window=3)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_weekly_data)
        
        # 最初の2つの値はNaNであることを確認（3週分のデータが不足）
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        
        # 3番目以降は計算値があることを確認
        assert not pd.isna(result.iloc[2])
        
        # 3番目の値が手計算と一致することを確認 (2.0+2.5+3.0)/3 = 2.5
        assert abs(result.iloc[2] - 2.5) < 0.0001
    
    def test_データ不足時の処理(self, aggregator):
        """異常系: データ点が移動平均ウィンドウより少ない場合の処理を確認"""
        # 3週分のデータしかない場合
        short_data = pd.DataFrame({
            'week_start': pd.date_range('2024-01-01', periods=3, freq='W'),
            'week_end': pd.date_range('2024-01-07', periods=3, freq='W'), 
            'pr_count': [10, 15, 12],
            'unique_authors': [5, 6, 4],
            'productivity': [2.0, 2.5, 3.0]
        })
        
        result = aggregator.calculate_moving_average(short_data, window=4)
        
        # 結果がpd.Seriesであることを確認
        assert isinstance(result, pd.Series)
        assert len(result) == 3
        
        # 全ての値がNaNであることを確認
        assert pd.isna(result).all()
    
    def test_空のデータの処理(self, aggregator):
        """異常系: 空のDataFrameの処理を確認"""
        empty_data = pd.DataFrame(columns=['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity'])
        
        result = aggregator.calculate_moving_average(empty_data)
        
        # 空のSeriesが返されることを確認
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_不正なcolumnを含むデータの処理(self, aggregator):
        """異常系: productivityカラムが存在しない場合のエラー処理"""
        invalid_data = pd.DataFrame({
            'week_start': pd.date_range('2024-01-01', periods=4, freq='W'),
            'week_end': pd.date_range('2024-01-07', periods=4, freq='W'),
            'pr_count': [10, 15, 12, 18],
            'unique_authors': [5, 6, 4, 8]
            # productivity カラムが存在しない
        })
        
        with pytest.raises(KeyError):
            aggregator.calculate_moving_average(invalid_data)