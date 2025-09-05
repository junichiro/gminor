"""
基本的なグラフ生成機能を担当するモジュール
"""
from typing import List, Dict, Any
import pandas as pd
import plotly.graph_objects as go
import datetime

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
    
    def create_productivity_chart(self, weekly_data: pd.DataFrame, moving_average_window: int = 4) -> str:
        """
        週次生産性グラフを生成してHTMLを返す
        
        Args:
            weekly_data: 週次データのDataFrame（ProductivityAggregatorの出力）
                必要な列: week_start, week_end, pr_count, unique_authors, productivity
            moving_average_window: 移動平均のウィンドウサイズ（デフォルト: 4週）
        
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
        fig = self._create_figure(x_data, y_data, ma_data, moving_average_window)
        
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
        ma_data = weekly_data['moving_average'].tolist() if 'moving_average' in weekly_data.columns else []
        
        return x_data, y_data, ma_data
    
    def _create_figure(self, x_data: List[str], y_data: List[float], ma_data: List[float] = None, moving_average_window: int = 4) -> go.Figure:
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
                name=f'{moving_average_window}週移動平均',
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
        fig = self._create_figure([], [], [], 4)
        
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
    
    def calculate_statistics(self, weekly_data: pd.DataFrame, target_repositories: List[str]) -> Dict[str, Any]:
        """
        週次データから統計サマリーを計算する
        
        Args:
            weekly_data: 週次データのDataFrame
            target_repositories: 対象リポジトリのリスト
            
        Returns:
            統計サマリーを含む辞書
        """
        if weekly_data.empty:
            return {
                'average_productivity': 0.0,
                'max_productivity': 0.0,
                'min_productivity': 0.0,
                'max_productivity_week': 'N/A',
                'min_productivity_week': 'N/A',
                'total_prs': 0,
                'total_contributors': 0,
                'target_repositories': target_repositories
            }
        
        productivity_series = weekly_data['productivity']
        
        # 最大・最小生産性の週を特定
        max_idx = productivity_series.idxmax()
        min_idx = productivity_series.idxmin()
        
        max_week = weekly_data.loc[max_idx, 'week_start']
        min_week = weekly_data.loc[min_idx, 'week_start']
        
        # 日付をローカルタイムゾーンに変換してフォーマット
        max_week_str = self.timezone_handler.utc_to_local(max_week).strftime('%Y-%m-%d')
        min_week_str = self.timezone_handler.utc_to_local(min_week).strftime('%Y-%m-%d')
        
        return {
            'average_productivity': float(productivity_series.mean()),
            'max_productivity': float(productivity_series.max()),
            'min_productivity': float(productivity_series.min()),
            'max_productivity_week': max_week_str,
            'min_productivity_week': min_week_str,
            'total_prs': int(weekly_data['pr_count'].sum()),
            # NOTE: 現在の実装では週ごとのユニーク作者数の最大値を使用しています。
            # 正確な総貢献者数（期間全体のユニーク作者数）を計算するには、
            # 生のPRデータからユニーク作者を数える必要があります（要データ層修正）
            'total_contributors': int(weekly_data['unique_authors'].max()),
            'target_repositories': target_repositories
        }
    
    def generate_html_report(self, weekly_data: pd.DataFrame, target_repositories: List[str], moving_average_window: int = 4) -> str:
        """
        メタデータと統計サマリーを含む完全なHTMLレポートを生成する
        
        Args:
            weekly_data: 週次データのDataFrame
            target_repositories: 対象リポジトリのリスト
            moving_average_window: 移動平均のウィンドウサイズ（デフォルト: 4）
            
        Returns:
            完全なHTMLレポートの文字列
        """
        # 統計データを計算
        stats = self.calculate_statistics(weekly_data, target_repositories)
        
        # グラフのHTMLを生成
        chart_html = self.create_productivity_chart(weekly_data, moving_average_window)
        
        # メタデータセクションを生成
        metadata_html = self._generate_metadata_html(weekly_data, target_repositories)
        
        # 統計サマリーセクションを生成
        statistics_html = self._generate_statistics_html(stats)
        
        # 完全なHTMLを組み立て
        return self._combine_html_sections(metadata_html, statistics_html, chart_html)
    
    def _generate_metadata_html(self, weekly_data: pd.DataFrame, target_repositories: List[str]) -> str:
        """
        メタデータセクションのHTMLを生成
        
        Args:
            weekly_data: 週次データのDataFrame
            target_repositories: 対象リポジトリのリスト
            
        Returns:
            メタデータセクションのHTML文字列
        """
        # 現在時刻を設定されたタイムゾーンで取得
        now = datetime.datetime.now(self.timezone_handler._display_tz)
        # タイムゾーン名を動的に取得（例：JST, PST, etc.）
        tz_name = now.strftime('%Z') or self.timezone_handler.display_timezone.split('/')[-1]
        generation_time = f"{now.strftime('%Y-%m-%d %H:%M')} {tz_name}"
        
        # 対象期間を計算
        if not weekly_data.empty:
            start_date = self.timezone_handler.utc_to_local(weekly_data['week_start'].min()).strftime('%Y-%m-%d')
            end_date = self.timezone_handler.utc_to_local(weekly_data['week_end'].max()).strftime('%Y-%m-%d')
            period = f"{start_date} 〜 {end_date}"
        else:
            period = "N/A"
        
        # リポジトリリストを文字列に変換
        repositories_str = ', '.join(target_repositories) if target_repositories else "N/A"
        
        return f'''
        <div class="metadata">
            <p>生成日時: {generation_time}</p>
            <p>対象期間: {period}</p>
            <p>対象リポジトリ: {repositories_str}</p>
        </div>
        '''
    
    def _generate_statistics_html(self, stats: Dict[str, Any]) -> str:
        """
        統計サマリーセクションのHTMLを生成
        
        Args:
            stats: 統計データの辞書
            
        Returns:
            統計サマリーセクションのHTML文字列
        """
        return f'''
        <div class="statistics">
            <h2>統計サマリー</h2>
            <ul>
                <li>平均生産性: {stats['average_productivity']:.2f}</li>
                <li>最高生産性: {stats['max_productivity']:.2f}（{stats['max_productivity_week']} の週）</li>
                <li>最低生産性: {stats['min_productivity']:.2f}（{stats['min_productivity_week']} の週）</li>
                <li>総 PR 数: {stats['total_prs']}</li>
                <li>総貢献者数: {stats['total_contributors']}</li>
            </ul>
        </div>
        '''
    
    def _combine_html_sections(self, metadata_html: str, statistics_html: str, chart_html: str) -> str:
        """
        HTMLセクションを組み合わせて完全なHTMLドキュメントを作成
        
        Args:
            metadata_html: メタデータセクションのHTML
            statistics_html: 統計セクションのHTML
            chart_html: グラフのHTML
            
        Returns:
            完全なHTMLドキュメント
        """
        # グラフのHTMLから<html>タグを除去してbodyの内容のみを取得
        chart_body = self._extract_chart_body(chart_html)
        
        return self._get_html_template().format(
            metadata_html=metadata_html,
            statistics_html=statistics_html,
            chart_body=chart_body
        )
    
    def _get_html_template(self) -> str:
        """
        HTMLレポートのテンプレートを取得
        
        Returns:
            HTMLテンプレート文字列
        """
        return '''<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>生産性レポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metadata {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .statistics {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .statistics ul {{ list-style-type: none; padding: 0; }}
                .statistics li {{ margin: 5px 0; }}
                h2 {{ color: #333; margin-top: 0; }}
                .metadata p {{ margin: 8px 0; }}
            </style>
        </head>
        <body>
            {metadata_html}
            {statistics_html}
            {chart_body}
        </body>
        </html>'''
    
    def _extract_chart_body(self, chart_html: str) -> str:
        """
        グラフのHTMLからbodyの内容を抽出
        
        Args:
            chart_html: PlotlyのHTML文字列
            
        Returns:
            bodyの内容のみのHTML
        """
        try:
            # PlotlyのHTMLからbodyの内容を抽出
            if '<body>' in chart_html and '</body>' in chart_html:
                start_idx = chart_html.find('<body>') + len('<body>')
                end_idx = chart_html.find('</body>')
                return chart_html[start_idx:end_idx].strip()
            
            # bodyタグがない場合は<div>から抽出
            if '<div' in chart_html and 'plotly' in chart_html.lower():
                start_idx = chart_html.find('<div')
                if start_idx != -1:
                    # script要素も含めて返す
                    return chart_html[start_idx:]
                    
            return chart_html
        except (ValueError, AttributeError):
            # エラーが発生した場合はそのまま返す
            return chart_html