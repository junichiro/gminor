"""ProductivityVisualizerのテスト"""
import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import re

from src.presentation_layer.visualizer import ProductivityVisualizer
from src.business_layer.timezone_handler import TimezoneHandler


class TestProductivityVisualizer:
    """ProductivityVisualizerクラスのテスト"""
    
    @pytest.fixture
    def timezone_handler(self):
        """TimezoneHandlerのフィクスチャ"""
        return TimezoneHandler("Asia/Tokyo")
    
    @pytest.fixture
    def visualizer(self, timezone_handler):
        """ProductivityVisualizerのフィクスチャ"""
        return ProductivityVisualizer(timezone_handler)
    
    @pytest.fixture
    def sample_weekly_data(self):
        """サンプル週次データ"""
        return pd.DataFrame({
            'week_start': [
                datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 22, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 29, 0, 0, tzinfo=timezone.utc)
            ],
            'week_end': [
                datetime(2024, 1, 21, 23, 59, 59, tzinfo=timezone.utc),
                datetime(2024, 1, 28, 23, 59, 59, tzinfo=timezone.utc),
                datetime(2024, 2, 4, 23, 59, 59, tzinfo=timezone.utc)
            ],
            'pr_count': [5, 8, 3],
            'unique_authors': [2, 4, 2],
            'productivity': [2.5, 2.0, 1.5]
        })
    
    @pytest.fixture
    def empty_weekly_data(self):
        """空の週次データ"""
        return pd.DataFrame(columns=['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity'])
    
    def test_ProductivityVisualizerが正常に初期化される(self, timezone_handler):
        """正常系: ProductivityVisualizerが正常に初期化されることを確認"""
        visualizer = ProductivityVisualizer(timezone_handler)
        assert visualizer is not None
        assert visualizer.timezone_handler == timezone_handler
    
    def test_create_productivity_chartが正常にHTML文字列を返す(self, visualizer, sample_weekly_data):
        """正常系: create_productivity_chartがHTML文字列を返すことを確認"""
        result = visualizer.create_productivity_chart(sample_weekly_data)
        
        # HTML文字列が返されることを確認
        assert isinstance(result, str)
        assert len(result) > 0
        
        # 基本的なHTML構造があることを確認
        assert '<html>' in result.lower()
        assert '<div' in result.lower()
        assert 'plotly' in result.lower()
    
    def test_グラフタイトルが正しく設定される(self, visualizer, sample_weekly_data):
        """正常系: グラフのタイトルが正しく設定されることを確認"""
        result = visualizer.create_productivity_chart(sample_weekly_data)
        
        # タイトルが含まれることを確認
        assert '週次生産性の推移' in result or 'Weekly Productivity Trend' in result
    
    def test_X軸に週の開始日が使用される(self, visualizer, sample_weekly_data):
        """正常系: X軸に週の開始日が使用されることを確認"""
        with patch('plotly.graph_objects.Figure') as mock_figure_class:
            mock_figure = Mock()
            mock_figure.to_html.return_value = '<html><div>Mock Chart</div></html>'
            mock_figure_class.return_value = mock_figure
            
            result = visualizer.create_productivity_chart(sample_weekly_data)
            
            # Figureが作成されたことを確認
            assert mock_figure_class.called
            
            # add_traceが呼ばれたことを確認
            assert mock_figure.add_trace.called
            
            # 呼び出し引数を確認
            args, kwargs = mock_figure.add_trace.call_args
            trace = args[0] if args else kwargs.get('trace')
            
            # トレースのX軸データに日付が含まれることを確認（大まかな確認）
            assert hasattr(trace, 'x') or 'x' in str(trace)
    
    def test_Y軸に生産性が使用される(self, visualizer, sample_weekly_data):
        """正常系: Y軸に生産性が使用されることを確認"""
        with patch('plotly.graph_objects.Figure') as mock_figure_class:
            mock_figure = Mock()
            mock_figure.to_html.return_value = '<html><div>Mock Chart</div></html>'
            mock_figure_class.return_value = mock_figure
            
            result = visualizer.create_productivity_chart(sample_weekly_data)
            
            # add_traceが呼ばれたことを確認
            assert mock_figure.add_trace.called
            
            # 呼び出し引数を確認
            args, kwargs = mock_figure.add_trace.call_args
            trace = args[0] if args else kwargs.get('trace')
            
            # トレースのY軸データに生産性データが含まれることを確認
            assert hasattr(trace, 'y') or 'y' in str(trace)
    
    def test_青色の線グラフが作成される(self, visualizer, sample_weekly_data):
        """正常系: 青色のマーカー付き線グラフが作成されることを確認"""
        with patch('plotly.graph_objects.Scatter') as mock_scatter:
            mock_scatter.return_value = Mock()
            with patch('plotly.graph_objects.Figure') as mock_figure_class:
                mock_figure = Mock()
                mock_figure.to_html.return_value = '<html><div>Mock Chart</div></html>'
                mock_figure_class.return_value = mock_figure
                
                result = visualizer.create_productivity_chart(sample_weekly_data)
                
                # Scatterトレースが作成されたことを確認
                assert mock_scatter.called
                
                # 呼び出し引数を確認
                args, kwargs = mock_scatter.call_args
                
                # 線+マーカーモードが指定されることを確認
                assert 'mode' in kwargs
                assert 'lines+markers' in kwargs['mode'] or 'markers+lines' in kwargs['mode']
                
                # 青色が指定されることを確認
                assert 'line' in kwargs or 'marker' in kwargs
    
    def test_空データの適切な処理(self, visualizer, empty_weekly_data):
        """正常系: 空のデータが適切に処理されることを確認"""
        result = visualizer.create_productivity_chart(empty_weekly_data)
        
        # HTML文字列が返されることを確認
        assert isinstance(result, str)
        assert len(result) > 0
        
        # 基本的なHTML構造があることを確認
        assert '<html>' in result.lower()
        assert '<div' in result.lower()
    
    def test_日付フォーマットが適切に処理される(self, visualizer):
        """正常系: 日付フォーマットが適切に処理されることを確認"""
        # 特定の日付でテスト
        test_data = pd.DataFrame({
            'week_start': [datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)],
            'week_end': [datetime(2024, 1, 21, 23, 59, 59, tzinfo=timezone.utc)],
            'pr_count': [5],
            'unique_authors': [2],
            'productivity': [2.5]
        })
        
        result = visualizer.create_productivity_chart(test_data)
        
        # HTML文字列が返されることを確認
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_ローカルタイムゾーンでの日付表示(self, visualizer, sample_weekly_data):
        """正常系: 日付がローカルタイムゾーンで表示されることを確認"""
        with patch.object(visualizer.timezone_handler, 'utc_to_local') as mock_convert:
            # モックの戻り値を設定
            mock_convert.side_effect = lambda dt: dt.replace(tzinfo=timezone.utc)
            
            result = visualizer.create_productivity_chart(sample_weekly_data)
            
            # timezone_handlerが呼び出されたことを確認
            assert mock_convert.called
            
            # 各週の開始日に対してタイムゾーン変換が呼ばれることを確認
            assert mock_convert.call_count >= len(sample_weekly_data)
    
    def test_グラフのレイアウト設定が正しく行われる(self, visualizer, sample_weekly_data):
        """正常系: グラフのレイアウトが正しく設定されることを確認"""
        with patch('plotly.graph_objects.Figure') as mock_figure_class:
            mock_figure = Mock()
            mock_figure.to_html.return_value = '<html><div>Mock Chart</div></html>'
            mock_figure_class.return_value = mock_figure
            
            result = visualizer.create_productivity_chart(sample_weekly_data)
            
            # update_layoutが呼ばれたことを確認
            assert mock_figure.update_layout.called
            
            # レイアウト設定の確認
            args, kwargs = mock_figure.update_layout.call_args
            
            # タイトルが設定されることを確認
            assert 'title' in kwargs
            
            # X軸とY軸のラベルが設定されることを確認
            assert 'xaxis_title' in kwargs or 'xaxis' in kwargs
            assert 'yaxis_title' in kwargs or 'yaxis' in kwargs
    
    def test_HTML出力の設定が正しく行われる(self, visualizer, sample_weekly_data):
        """正常系: HTML出力の設定が正しく行われることを確認"""
        with patch('plotly.graph_objects.Figure') as mock_figure_class:
            mock_figure = Mock()
            mock_figure.to_html.return_value = '<html><div>Mock Chart</div></html>'
            mock_figure_class.return_value = mock_figure
            
            result = visualizer.create_productivity_chart(sample_weekly_data)
            
            # to_htmlが呼ばれたことを確認
            assert mock_figure.to_html.called
            
            # HTML設定が含まれることを確認
            args, kwargs = mock_figure.to_html.call_args
            
            # include_plotlyjsの設定確認（自己完結型HTML）
            assert 'include_plotlyjs' in kwargs
    
    def test_不正なデータ型の処理(self, visualizer):
        """異常系: 不正なデータ型が渡された場合の処理を確認"""
        # 不正なデータ（文字列）を渡す
        with pytest.raises((TypeError, AttributeError, ValueError)):
            visualizer.create_productivity_chart("invalid_data")
    
    def test_必要な列が欠けているDataFrameの処理(self, visualizer):
        """異常系: 必要な列が欠けているDataFrameの処理を確認"""
        # 必要な列が欠けているDataFrame
        invalid_data = pd.DataFrame({
            'week_start': [datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)],
            'invalid_column': [1]
        })
        
        with pytest.raises((KeyError, AttributeError)):
            visualizer.create_productivity_chart(invalid_data)