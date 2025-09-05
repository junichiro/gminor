"""データベース接続・セッション管理

このモジュールはSQLAlchemyを使用したデータベース接続の管理と
セッションの提供を担当します。
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.pool import StaticPool

from .models import Base, DatabaseError

# ログ設定
logger = logging.getLogger(__name__)


class DatabaseManager:
    """データベース接続・セッション管理クラス
    
    SQLiteデータベースへの接続管理とセッションの提供を行います。
    コンテキストマネージャーパターンを使用して、適切なセッション管理を実現します。
    """
    
    def __init__(self, db_path: str, echo: bool = False) -> None:
        """DatabaseManagerを初期化
        
        Args:
            db_path: データベースファイルのパス
            echo: SQLクエリのログ出力を有効にするか（デフォルト: False）
            
        Raises:
            DatabaseError: データベースディレクトリが存在しない、または書き込み権限がない場合
        """
        self.db_path = db_path
        self._echo = echo
        
        logger.info(f"Initializing DatabaseManager for: {db_path}")
        
        # データベースファイルの親ディレクトリをチェック
        db_dir = Path(db_path).parent
        
        # ディレクトリが存在しない場合
        if not db_dir.exists():
            error_msg = f"Database directory does not exist: {db_dir}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
        
        # ディレクトリに書き込み権限がない場合
        if not os.access(db_dir, os.W_OK):
            error_msg = f"Cannot write to database directory: {db_dir}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
        
        try:
            # SQLiteデータベースエンジンを作成
            self.engine: Engine = create_engine(
                f"sqlite:///{db_path}",
                echo=self._echo,  # SQLログの設定
                pool_pre_ping=True,  # 接続の生存確認
                poolclass=StaticPool,  # SQLite用の接続プール
                connect_args={
                    "check_same_thread": False,  # マルチスレッド対応
                    "timeout": 30,  # 接続タイムアウト30秒
                    "isolation_level": None  # 自動コミットモードを無効化
                }
            )
            
            # スレッドセーフなセッションファクトリーを作成
            session_factory = sessionmaker(bind=self.engine)
            self.SessionFactory = scoped_session(session_factory)
            
            logger.info("Database engine initialized successfully")
            
        except SQLAlchemyError as e:
            error_msg = f"Failed to initialize database engine: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def initialize_database(self) -> None:
        """データベースの初期化
        
        テーブルとインデックスを作成します。
        既存のテーブルがある場合は何も行いません（べき等性を保証）。
        
        Raises:
            DatabaseError: テーブル作成に失敗した場合
        """
        try:
            logger.info("Initializing database tables and indexes")
            
            # すべてのテーブルを作成（存在しない場合のみ）
            Base.metadata.create_all(self.engine)
            
            # 作成されたテーブル一覧をログ出力
            table_names = list(Base.metadata.tables.keys())
            logger.info(f"Database initialized with tables: {table_names}")
            
        except OperationalError as e:
            error_msg = f"Database operation failed during initialization: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
        except SQLAlchemyError as e:
            error_msg = f"Failed to initialize database tables: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """データベースセッションを取得（コンテキストマネージャー）
        
        使用例:
            with db_manager.get_session() as session:
                user = session.query(User).first()
                # トランザクションは自動的にコミットまたはロールバックされる
        
        Yields:
            Session: SQLAlchemyセッション
            
        Raises:
            DatabaseError: セッション作成に失敗した場合
        """
        session: Optional[Session] = None
        
        try:
            session = self.SessionFactory()
            logger.debug("Database session created")
            
            yield session
            
            # 正常終了時は自動的にコミット
            session.commit()
            logger.debug("Database session committed")
            
        except OperationalError as e:
            # データベース操作エラー
            if session:
                session.rollback()
                logger.warning(f"Database session rolled back due to operational error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
            
        except Exception as e:
            # 一般的なエラー発生時は自動的にロールバック
            if session:
                session.rollback()
                logger.warning(f"Database session rolled back due to error: {e}")
            raise
            
        finally:
            # 必ずセッションを閉じる
            if session:
                session.close()
                logger.debug("Database session closed")
            
            # スコープされたセッションのクリーンアップ
            self.SessionFactory.remove()
    
    def close(self) -> None:
        """DatabaseManagerを終了し、接続プールを閉じる
        
        アプリケーション終了時に呼び出すことを推奨します。
        """
        try:
            self.SessionFactory.remove()
            self.engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def health_check(self) -> bool:
        """データベース接続の健全性をチェック
        
        Returns:
            bool: 接続が正常な場合True、異常な場合False
        """
        try:
            with self.get_session() as session:
                # シンプルなクエリを実行して接続を確認
                session.execute("SELECT 1")
            logger.debug("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_weekly_metrics(self) -> 'pandas.DataFrame':
        """週次メトリクスデータを取得
        
        データベースからプルリクエストデータを取得し、
        ProductivityVisualizerで使用可能な形式の週次メトリクスを計算して返します。
        
        Returns:
            pandas.DataFrame: 週次メトリクスのDataFrame
                必要な列: week_start, week_end, pr_count, unique_authors, productivity
        
        Raises:
            DatabaseError: データ取得に失敗した場合
        """
        try:
            import pandas as pd
            from datetime import datetime, timezone, timedelta
            from sqlalchemy import func, and_
            from .models import PullRequest
            
            with self.get_session() as session:
                # マージされたPRのみを対象にクエリを実行
                query = session.query(
                    PullRequest.merged_at,
                    PullRequest.author,
                    PullRequest.pr_number
                ).filter(
                    PullRequest.merged_at.isnot(None)
                ).order_by(PullRequest.merged_at)
                
                results = query.all()
                
                if not results:
                    # 空のDataFrameを返す
                    return pd.DataFrame(columns=['week_start', 'week_end', 'pr_count', 'unique_authors', 'productivity'])
                
                # プルリクエストデータをリスト形式に変換
                pr_data = []
                for merged_at, author, pr_number in results:
                    pr_data.append({
                        'merged_at': merged_at,
                        'author': author,
                        'number': pr_number
                    })
                
                # ProductivityAggregatorと同様の処理でweekly_dataを作成
                from ..business_layer.aggregator import ProductivityAggregator
                from ..business_layer.timezone_handler import TimezoneHandler
                
                # デフォルトのタイムゾーンハンドラーを使用
                timezone_handler = TimezoneHandler()
                aggregator = ProductivityAggregator(timezone_handler)
                
                weekly_metrics = aggregator.calculate_weekly_metrics(pr_data)
                
                logger.info(f"Retrieved {len(weekly_metrics)} weeks of metrics data")
                return weekly_metrics
                
        except Exception as e:
            error_msg = f"Failed to retrieve weekly metrics: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)