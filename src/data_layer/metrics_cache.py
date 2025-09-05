"""メトリクスキャッシュモジュール - 週次メトリクスの効率的なキャッシュ管理"""
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import hashlib
import json
import pandas as pd
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    data: pd.DataFrame
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """キャッシュが期限切れかどうかを確認"""
        expiry_time = self.created_at.timestamp() + self.ttl_seconds
        return time.time() > expiry_time


class MetricsCache:
    """週次メトリクスの効率的なキャッシュ管理クラス"""
    
    def __init__(self, default_ttl_seconds: int = 3600):
        """
        MetricsCacheを初期化
        
        Args:
            default_ttl_seconds: デフォルトTTL秒数（デフォルト: 3600秒 = 1時間）
        """
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        logger.info(f"MetricsCache initialized with default TTL: {default_ttl_seconds}s")
    
    def get_cached_weekly_metrics(self, repo_name: str, timezone_name: str = "UTC") -> pd.DataFrame:
        """
        キャッシュされた週次メトリクスを取得
        
        Args:
            repo_name: リポジトリ名
            timezone_name: タイムゾーン名（デフォルト: "UTC"）
            
        Returns:
            pd.DataFrame: 週次メトリクスデータ
        """
        start_time = time.time()
        cache_key = self._generate_cache_key(repo_name, timezone_name)
        
        logger.debug(f"Retrieving cached weekly metrics for {repo_name} (timezone: {timezone_name})")
        
        # キャッシュ確認
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            if not entry.is_expired():
                # キャッシュヒット
                retrieval_time = time.time() - start_time
                logger.info(f"Cache hit for {repo_name}: retrieved in {retrieval_time:.3f}s")
                return entry.data.copy()
            else:
                # 期限切れキャッシュを削除
                del self._cache[cache_key]
                logger.debug(f"Expired cache entry removed for {repo_name}")
        
        # キャッシュミス - 新規計算
        logger.info(f"Cache miss for {repo_name} - computing weekly metrics")
        computed_data = self._compute_weekly_metrics(repo_name, timezone_name)
        
        # キャッシュに保存
        self._cache[cache_key] = CacheEntry(
            data=computed_data.copy(),
            created_at=datetime.now(timezone.utc),
            ttl_seconds=self.default_ttl_seconds
        )
        
        retrieval_time = time.time() - start_time
        logger.info(f"Weekly metrics computed and cached for {repo_name}: {retrieval_time:.3f}s")
        
        return computed_data
    
    def is_cached(self, repo_name: str, timezone_name: str = "UTC") -> bool:
        """
        指定されたデータがキャッシュされているかを確認
        
        Args:
            repo_name: リポジトリ名
            timezone_name: タイムゾーン名
            
        Returns:
            bool: キャッシュされている場合True
        """
        cache_key = self._generate_cache_key(repo_name, timezone_name)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired():
                return True
            else:
                # 期限切れキャッシュを削除
                del self._cache[cache_key]
        
        return False
    
    def invalidate_cache(self, repo_name: str, timezone_name: str = "UTC") -> bool:
        """
        指定されたキャッシュエントリを無効化
        
        Args:
            repo_name: リポジトリ名  
            timezone_name: タイムゾーン名
            
        Returns:
            bool: 無効化されたエントリが存在した場合True
        """
        cache_key = self._generate_cache_key(repo_name, timezone_name)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.info(f"Cache invalidated for {repo_name} (timezone: {timezone_name})")
            return True
        
        return False
    
    def clear_all_cache(self) -> int:
        """
        すべてのキャッシュエントリをクリア
        
        Returns:
            int: クリアされたエントリ数
        """
        cleared_count = len(self._cache)
        self._cache.clear()
        logger.info(f"All cache entries cleared: {cleared_count} entries")
        return cleared_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        キャッシュ統計情報を取得
        
        Returns:
            Dict[str, Any]: キャッシュ統計情報
        """
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
        valid_entries = total_entries - expired_entries
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_hit_ratio': self._calculate_hit_ratio(),
            'default_ttl_seconds': self.default_ttl_seconds
        }
    
    def _generate_cache_key(self, repo_name: str, timezone_name: str) -> str:
        """
        キャッシュキーを生成
        
        Args:
            repo_name: リポジトリ名
            timezone_name: タイムゾーン名
            
        Returns:
            str: ハッシュ化されたキャッシュキー
        """
        key_data = {
            'repo_name': repo_name,
            'timezone': timezone_name,
            'type': 'weekly_metrics'
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _compute_weekly_metrics(self, repo_name: str, timezone_name: str) -> pd.DataFrame:
        """
        週次メトリクスを計算（実装は将来の段階で行う）
        
        Args:
            repo_name: リポジトリ名
            timezone_name: タイムゾーン名
            
        Returns:
            pd.DataFrame: 計算された週次メトリクス
        """
        # 現在は簡単なサンプルデータを返す（後でデータベースクエリに置き換え予定）
        logger.info(f"Computing weekly metrics for {repo_name} (timezone: {timezone_name})")
        
        # サンプルの週次データを生成
        dates = pd.date_range('2024-01-01', periods=52, freq='W')
        sample_data = pd.DataFrame({
            'week_start': dates,
            'repo_name': [repo_name] * 52,
            'pr_count': [10, 15, 8, 12, 20] * 10 + [5, 7],
            'unique_authors': [3, 4, 2, 3, 5] * 10 + [2, 3],
            'timezone': [timezone_name] * 52
        })
        
        return sample_data
    
    def _calculate_hit_ratio(self) -> float:
        """
        キャッシュヒット率を計算（簡易版）
        
        Returns:
            float: キャッシュヒット率（0.0-1.0）
        """
        # 実装の簡易化のため、現在は固定値を返す
        # 実際の実装では、ヒット数とミス数を追跡する必要がある
        return 0.85  # 85%のヒット率と仮定