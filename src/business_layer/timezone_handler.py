"""
タイムゾーン処理を担当するモジュール
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class TimezoneHandler:
    """タイムゾーン変換とメンテナンス処理を担当するクラス"""
    
    def __init__(self, display_timezone: str = "Asia/Tokyo"):
        """
        表示用タイムゾーンを設定
        
        Args:
            display_timezone: 表示用のタイムゾーン（デフォルト: Asia/Tokyo）
        """
        self.display_timezone = display_timezone
        self._display_tz = ZoneInfo(display_timezone)
        self._utc_tz = ZoneInfo("UTC")
    
    def _ensure_timezone(self, dt: datetime, default_tz: str) -> datetime:
        """
        datetimeオブジェクトがタイムゾーン情報を持っていることを確保する
        
        Args:
            dt: 対象のdatetimeオブジェクト
            default_tz: デフォルトのタイムゾーン名
            
        Returns:
            タイムゾーン情報を持つdatetimeオブジェクト
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=ZoneInfo(default_tz))
        return dt
    
    def utc_to_local(self, dt: datetime) -> datetime:
        """
        UTCから設定されたタイムゾーンに変換
        
        Args:
            dt: UTC時刻のdatetimeオブジェクト
            
        Returns:
            ローカルタイムゾーンのdatetimeオブジェクト
        """
        # タイムゾーン情報を持たない場合はUTCとして扱う
        dt = self._ensure_timezone(dt, "UTC")
        
        # 指定されたタイムゾーンに変換
        return dt.astimezone(self._display_tz)
    
    def local_to_utc(self, dt: datetime) -> datetime:
        """
        設定されたタイムゾーンからUTCに変換
        
        Args:
            dt: ローカル時刻のdatetimeオブジェクト
            
        Returns:
            UTC時刻のdatetimeオブジェクト
        """
        # タイムゾーン情報を持たない場合は設定されたタイムゾーンとして扱う
        dt = self._ensure_timezone(dt, self.display_timezone)
        
        # UTCに変換
        return dt.astimezone(self._utc_tz)
    
    def get_week_boundaries(self, date: datetime) -> tuple[datetime, datetime]:
        """
        指定日付を含む週の開始・終了日時を返す（ローカルタイムゾーン）
        
        Args:
            date: 対象日付
            
        Returns:
            週の開始日時と終了日時のタプル
        """
        # タイムゾーン情報を持たない場合は設定されたタイムゾーンとして扱う
        date = self._ensure_timezone(date, self.display_timezone)
        
        # 月曜日を0として、現在の曜日を取得
        weekday = date.weekday()  # 0=月曜日, 6=日曜日
        
        # 週の開始（月曜日の0:00）
        start_date = date - timedelta(days=weekday)
        start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 週の終了（日曜日の23:59:59）
        end_date = start_date + timedelta(days=6)
        end = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start, end