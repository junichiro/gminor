"""
TimezoneHandlerクラスのテスト
"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ の標準ライブラリ
from src.business_layer.timezone_handler import TimezoneHandler


class TestTimezoneHandler(unittest.TestCase):
    """TimezoneHandlerクラスのテスト"""

    def test_utc_to_local_conversion(self):
        """UTCの日時を日本時間に変換できることを確認"""
        # Arrange
        handler = TimezoneHandler()
        utc_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC"))
        
        # Act
        local_dt = handler.utc_to_local(utc_dt)
        
        # Assert
        # UTC 10:30 は 日本時間 19:30
        assert local_dt.hour == 19
        assert local_dt.minute == 30
        assert str(local_dt.tzinfo) == "Asia/Tokyo"
    
    def test_local_to_utc_conversion(self):
        """日本時間の日時をUTCに変換できることを確認"""
        # Arrange
        handler = TimezoneHandler()
        local_dt = datetime(2024, 1, 15, 19, 30, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        
        # Act
        utc_dt = handler.local_to_utc(local_dt)
        
        # Assert
        # 日本時間 19:30 は UTC 10:30
        assert utc_dt.hour == 10
        assert utc_dt.minute == 30
        assert str(utc_dt.tzinfo) == "UTC"
    
    def test_get_week_boundaries_monday_start(self):
        """指定日付を含む週の開始・終了日時を取得できることを確認"""
        # Arrange
        handler = TimezoneHandler()
        # 2024年1月15日（月曜日）の場合
        target_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        
        # Act
        start, end = handler.get_week_boundaries(target_date)
        
        # Assert
        # 週の開始は2024年1月15日（月）0:00
        assert start.year == 2024
        assert start.month == 1
        assert start.day == 15
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0
        assert str(start.tzinfo) == "Asia/Tokyo"
        
        # 週の終了は2024年1月21日（日）23:59:59
        assert end.year == 2024
        assert end.month == 1
        assert end.day == 21
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59
        assert str(end.tzinfo) == "Asia/Tokyo"
    
    def test_get_week_boundaries_midweek(self):
        """週の途中の日付でも正しく週境界を取得できることを確認"""
        # Arrange
        handler = TimezoneHandler()
        # 2024年1月17日（水曜日）の場合
        target_date = datetime(2024, 1, 17, 15, 30, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        
        # Act
        start, end = handler.get_week_boundaries(target_date)
        
        # Assert
        # 週の開始は2024年1月15日（月）0:00
        assert start.year == 2024
        assert start.month == 1
        assert start.day == 15
        assert start.hour == 0
        assert start.minute == 0
        
        # 週の終了は2024年1月21日（日）23:59:59
        assert end.year == 2024
        assert end.month == 1
        assert end.day == 21
        assert end.hour == 23
        assert end.minute == 59
    
    def test_different_timezone_specification(self):
        """デフォルト以外のタイムゾーンを指定できることを確認"""
        # Arrange
        handler = TimezoneHandler(display_timezone="America/New_York")
        utc_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC"))
        
        # Act
        local_dt = handler.utc_to_local(utc_dt)
        
        # Assert
        # UTC 10:30 は ニューヨーク時間 5:30
        assert local_dt.hour == 5
        assert local_dt.minute == 30
        assert str(local_dt.tzinfo) == "America/New_York"


if __name__ == "__main__":
    unittest.main()