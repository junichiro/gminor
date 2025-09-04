"""SQLAlchemyモデル定義

このモジュールはgminorアプリケーションのデータベースモデルを定義します。
- PullRequest: GitHubプルリクエストの情報
- WeeklyMetrics: 週次集計データ（キャッシュ用）
- SyncStatus: リポジトリ同期状態の管理
"""
from datetime import datetime, timezone, date
from typing import Optional, ClassVar, Set
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates

# SQLAlchemyのベースクラス
Base = declarative_base()


class DatabaseError(Exception):
    """データベース関連のエラー"""
    pass


class PullRequest(Base):
    """プルリクエストモデル
    
    GitHubのプルリクエスト情報を格納するモデル。
    リポジトリとPR番号の組み合わせで一意性を保証する。
    """
    __tablename__ = 'pull_requests'
    
    # 主キー
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本フィールド
    repo_name = Column(String(255), nullable=False, comment="リポジトリ名（owner/repo形式）")
    pr_number = Column(Integer, nullable=False, comment="プルリクエスト番号")
    author = Column(String(255), nullable=False, comment="作成者のユーザー名")
    title = Column(String(1000), nullable=False, comment="プルリクエストのタイトル")
    merged_at = Column(DateTime(timezone=True), nullable=True, comment="マージ日時（未マージの場合はNULL）")
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), nullable=False, comment="作成日時")
    updated_at = Column(DateTime(timezone=True), nullable=False, comment="更新日時")
    
    # 制約とインデックス
    __table_args__ = (
        UniqueConstraint('repo_name', 'pr_number', name='uq_repo_pr_number'),
        Index('idx_repo_name', 'repo_name'),
        Index('idx_author', 'author'),
        Index('idx_merged_at', 'merged_at'),
        Index('idx_created_at', 'created_at'),
    )
    
    @property
    def is_merged(self) -> bool:
        """マージ済みかどうかを判定"""
        return self.merged_at is not None
    
    def get_full_identifier(self) -> str:
        """完全識別子を取得（repo_name#pr_number形式）"""
        return f"{self.repo_name}#{self.pr_number}"
    
    def __repr__(self) -> str:
        return (f"<PullRequest(id={self.id}, repo_name='{self.repo_name}', "
                f"pr_number={self.pr_number}, author='{self.author}', "
                f"merged={self.is_merged})>")


class WeeklyMetrics(Base):
    """週次メトリクスモデル（キャッシュ用）
    
    週単位での集計データを格納してパフォーマンスを向上させるためのモデル。
    週の開始日とリポジトリ名で一意性を保証する。
    """
    __tablename__ = 'weekly_metrics'
    
    # 主キー
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本フィールド
    week_start_date = Column(Date, nullable=False, comment="週の開始日（月曜日）")
    repo_name = Column(String(255), nullable=False, comment="リポジトリ名（owner/repo形式）")
    pr_count = Column(Integer, nullable=False, default=0, comment="総PR数")
    merged_pr_count = Column(Integer, nullable=False, default=0, comment="マージされたPR数")
    total_authors = Column(Integer, nullable=False, default=0, comment="ユニークな作成者数")
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), nullable=False, comment="作成日時")
    updated_at = Column(DateTime(timezone=True), nullable=False, comment="更新日時")
    
    # 制約とインデックス
    __table_args__ = (
        UniqueConstraint('week_start_date', 'repo_name', name='uq_week_repo'),
        Index('idx_week_start_date', 'week_start_date'),
        Index('idx_weekly_repo_name', 'repo_name'),
        Index('idx_week_repo_composite', 'week_start_date', 'repo_name'),
    )
    
    @validates('pr_count', 'merged_pr_count', 'total_authors')
    def validate_non_negative(self, key: str, value: int) -> int:
        """非負数の検証
        
        Args:
            key: フィールド名
            value: 設定する値
            
        Returns:
            int: 検証済みの値
            
        Raises:
            ValueError: 負数が指定された場合
        """
        if value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value
    
    @property
    def merge_rate(self) -> float:
        """マージ率を計算（0.0-1.0）"""
        if self.pr_count == 0:
            return 0.0
        return self.merged_pr_count / self.pr_count
    
    @property
    def week_end_date(self) -> date:
        """週の終了日を計算（日曜日）"""
        from datetime import timedelta
        return self.week_start_date + timedelta(days=6)
    
    def get_week_range_str(self) -> str:
        """週の範囲を文字列で取得"""
        return f"{self.week_start_date} - {self.week_end_date}"
    
    def __repr__(self) -> str:
        return (f"<WeeklyMetrics(id={self.id}, week_start_date={self.week_start_date}, "
                f"repo_name='{self.repo_name}', pr_count={self.pr_count}, "
                f"merge_rate={self.merge_rate:.2f})>")


class SyncStatus(Base):
    """同期状態管理モデル
    
    各リポジトリの同期状態を管理するためのモデル。
    GitHub APIからのデータ取得進捗とエラー状況を追跡する。
    """
    __tablename__ = 'sync_status'
    
    # ステータスの有効値を定数として定義
    VALID_STATUSES: ClassVar[Set[str]] = {'pending', 'in_progress', 'completed', 'error'}
    
    # 主キー
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本フィールド
    repo_name = Column(String(255), nullable=False, unique=True, comment="リポジトリ名（owner/repo形式）")
    last_synced_at = Column(DateTime(timezone=True), nullable=True, comment="最終同期日時")
    last_pr_number = Column(Integer, nullable=True, comment="最後に処理されたPR番号")
    status = Column(String(50), nullable=False, default='pending', comment="同期ステータス")
    error_message = Column(String(2000), nullable=True, comment="エラーメッセージ（エラー時のみ）")
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), nullable=False, comment="作成日時")
    updated_at = Column(DateTime(timezone=True), nullable=False, comment="更新日時")
    
    # インデックス
    __table_args__ = (
        Index('idx_sync_repo_name', 'repo_name'),
        Index('idx_sync_status', 'status'),
        Index('idx_last_synced_at', 'last_synced_at'),
    )
    
    @validates('status')
    def validate_status(self, key: str, value: str) -> str:
        """ステータスの検証
        
        Args:
            key: フィールド名（'status'）
            value: 設定する値
            
        Returns:
            str: 検証済みのステータス値
            
        Raises:
            ValueError: 無効なステータスが指定された場合
        """
        if value not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of {self.VALID_STATUSES}")
        return value
    
    def is_completed(self) -> bool:
        """同期が完了しているかを判定"""
        return self.status == 'completed'
    
    def is_error(self) -> bool:
        """エラー状態かを判定"""
        return self.status == 'error'
    
    def mark_completed(self, last_pr_number: Optional[int] = None) -> None:
        """完了状態に設定"""
        self.status = 'completed'
        self.error_message = None
        if last_pr_number is not None:
            self.last_pr_number = last_pr_number
        self.last_synced_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_error(self, error_message: str) -> None:
        """エラー状態に設定"""
        self.status = 'error'
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return (f"<SyncStatus(id={self.id}, repo_name='{self.repo_name}', "
                f"status='{self.status}', last_pr_number={self.last_pr_number})>")