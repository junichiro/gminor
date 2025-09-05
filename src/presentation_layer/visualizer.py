"""
基本的なグラフ生成機能を担当するモジュール
"""
from typing import List, Dict, Any
import pandas as pd
import plotly.graph_objects as go

from ..business_layer.timezone_handler import TimezoneHandler


class ProductivityVisualizer:
    """生産性グラフの可視化を担当するクラス"""
    
    # チャートの設定定数
    CHART_CONFIG = {
        'line_color': 'blue',
        'line_width': 2,
        'marker_size': 6,
        'template': 'plotly_white',
        'moving_average_color': 'red',
        'moving_average_dash': 'dash'
    }
    
    def __init__(self, timezone_handler: TimezoneHandler):
        """
        ProductivityVisualizerを初期化
        
        Args:
            timezone_handler: タイムゾーン処理を担当するハンドラー
        """
        self.timezone_handler = timezone_handler
    
    def create_productivity_chart(self, weekly_data: pd.DataFrame) -> str:
        """
        週次生産性グラフを生成してHTMLを返す
        
        Args:
            weekly_data: 週次データのDataFrame（ProductivityAggregatorの出力）
                必要な列: week_start, week_end, pr_count, unique_authors, productivity
        
        Returns:
            Plotlyで生成されたHTMLファイルの文字列
        
        Raises:
            KeyError: 必要な列が存在しない場合
            TypeError: 不正なデータ型が渡された場合
        """
        # データ検証
        self._validate_input_data(weekly_data)
        
        # 空データの処理
        if weekly_data.empty:
            return self._create_empty_chart()
        
        # データの前処理
        x_data, y_data, ma_data = self._prepare_chart_data(weekly_data)
        
        # グラフの作成
        fig = self._create_figure(x_data, y_data, ma_data)
        
        # レイアウトの適用
        self._apply_layout(fig)
        
        # HTMLとして出力
        return fig.to_html(include_plotlyjs='inline')
    
    def _validate_input_data(self, weekly_data: pd.DataFrame) -> None:
        """
        入力データの妥当性を検証
        
        Args:
            weekly_data: 検証対象のDataFrame
            
        Raises:
            TypeError: データ型が不正な場合
            KeyError: 必要な列が存在しない場合
        """
        # データ型チェック
        if not isinstance(weekly_data, pd.DataFrame):
            raise TypeError("weekly_data must be a pandas DataFrame")
        
        # 空データの場合は検証をスキップ
        if weekly_data.empty:
            return
        
        # 必要な列の存在チェック
        required_columns = ['week_start', 'productivity']
        missing_columns = [col for col in required_columns if col not in weekly_data.columns]
        if missing_columns:
            raise KeyError(f"Missing required columns: {missing_columns}")
    
    def _prepare_chart_data(self, weekly_data: pd.DataFrame) -> tuple[List[str], List[float], List[float]]:
        """
        チャート用のデータを準備（pandasの機能を活用して効率化）
        
        Args:
            weekly_data: 週次データのDataFrame
            
        Returns:
            Tuple[X軸データ（日付文字列のリスト）, Y軸データ（生産性のリスト）, 移動平均データ（移動平均のリスト）]
        """
        # X軸データの準備（pandasのapplyを使用してローカルタイムゾーンに変換）
        x_data = weekly_data['week_start'].apply(
            lambda dt: self.timezone_handler.utc_to_local(dt).strftime('%Y-%m-%d')
        ).tolist()
        
        # Y軸データ（生産性）- そのまま使用
        y_data = weekly_data['productivity'].tolist()
        
        # 移動平均データ（存在する場合）
        ma_data = []
        if 'moving_average' in weekly_data.columns:
            ma_data = weekly_data['moving_average'].tolist()
        
        return x_data, y_data, ma_data
    
    def _create_figure(self, x_data: List[str], y_data: List[float], ma_data: List[float] = None) -> go.Figure:
        """
        Plotly図表オブジェクトを作成
        
        Args:
            x_data: X軸データ
            y_data: Y軸データ
            ma_data: 移動平均データ（オプション）
            
        Returns:
            Plotly図表オブジェクト
        """
        fig = go.Figure()
        
        # 青色のマーカー付き線グラフを追加
        fig.add_trace(go.Scatter(
            x=x_data,
            y=y_data,
            mode='lines+markers',
            name='生産性',
            line=dict(
                color=self.CHART_CONFIG['line_color'],
                width=self.CHART_CONFIG['line_width']
            ),
            marker=dict(
                color=self.CHART_CONFIG['line_color'],
                size=self.CHART_CONFIG['marker_size']
            )
        ))
        
        # 移動平均線を追加（データが存在する場合）
        if ma_data:
            fig.add_trace(go.Scatter(
                x=x_data,
                y=ma_data,
                mode='lines',
                name='4週移動平均',
                line=dict(
                    color=self.CHART_CONFIG['moving_average_color'],
                    width=self.CHART_CONFIG['line_width'],
                    dash=self.CHART_CONFIG['moving_average_dash']
                )
            ))
        
        return fig
    
    def _apply_layout(self, fig: go.Figure) -> None:
        """
        図表のレイアウトを適用
        
        Args:
            fig: レイアウトを適用する図表オブジェクト
        """
        fig.update_layout(
            title='週次生産性の推移',
            xaxis_title='週の開始日',
            yaxis_title='生産性 (PR数/人)',
            hovermode='x unified',
            template=self.CHART_CONFIG['template'],
            showlegend=True
        )
    
    def _create_empty_chart(self) -> str:
        """
        空のデータ用のチャートを作成
        
        Returns:
            空のチャートのHTML文字列
        """
        # 空のデータでグラフを作成
        fig = self._create_figure([], [], [])
        
        # 基本レイアウトを適用
        self._apply_layout(fig)
        
        # 空データ用の注釈を追加
        self._add_empty_data_annotation(fig)
        
        return fig.to_html(include_plotlyjs='inline')
    
    def _add_empty_data_annotation(self, fig: go.Figure) -> None:
        """
        空データ用の注釈を図表に追加
        
        Args:
            fig: 注釈を追加する図表オブジェクト
        """
        fig.add_annotation(
            text='データがありません',
            xref='paper',
            yref='paper',
            x=0.5,
            y=0.5,
            xanchor='center',
            yanchor='middle',
            showarrow=False,
            font=dict(size=16, color='gray')
        )