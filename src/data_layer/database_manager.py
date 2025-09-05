"""データベース接続・セッション管理

このモジュールはSQLAlchemyを使用したデータベース接続の管理と
セッションの提供を担当します。
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, List, Dict, Any

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
    
    def get_merged_pull_requests(self) -> List[Dict[str, Any]]:
        """マージされたプルリクエストデータを取得
        
        データベースからマージされたプルリクエストの基本情報を取得します。
        ビジネス層で使用するためのデータのみを提供します。
        
        Returns:
            List[Dict[str, Any]]: プルリクエストデータのリスト
                各要素は {'merged_at': datetime, 'author': str, 'number': int} 形式
        
        Raises:
            DatabaseError: データ取得に失敗した場合
        """
        try:
            from .models import PullRequest
            
            logger.debug("Querying merged pull requests from database")
            with self.get_session() as session:
                # マージされたPRのみを対象にクエリを実行
                query = session.query(
                    PullRequest.merged_at,
                    PullRequest.author,
                    PullRequest.pr_number
                ).filter(
                    PullRequest.merged_at.isnot(None)
                ).order_by(PullRequest.merged_at)
                
                logger.debug(f"Executing query: {query}")
                results = query.all()
                
                # プルリクエストデータをリスト形式に変換
                pr_data = []
                for merged_at, author, pr_number in results:
                    pr_data.append({
                        'merged_at': merged_at,
                        'author': author,
                        'number': pr_number
                    })
                
                logger.debug(f"Successfully retrieved {len(pr_data)} merged pull requests")
                logger.info(f"Retrieved {len(pr_data)} merged pull requests")
                return pr_data
                
        except Exception as e:
            error_msg = f"Failed to retrieve merged pull requests: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def cleanup_old_data(self, before_date: str) -> Dict[str, int]:
        """
        指定日以前の古いデータをクリーンアップする
        
        Args:
            before_date: 削除対象の基準日（YYYY-MM-DD形式）
            
        Returns:
            削除されたレコード数を含む辞書
            
        Raises:
            DatabaseError: クリーンアップ処理に失敗した場合
        """
        try:
            from datetime import datetime, timezone
            from .models import PullRequest, WeeklyMetrics, SyncStatus
            
            # 日付をdatetimeオブジェクトに変換
            cutoff_date = datetime.strptime(before_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            with self.get_session() as session:
                # PRの削除
                deleted_prs = session.query(PullRequest).filter(
                    PullRequest.merged_at < cutoff_date
                ).delete()
                
                # WeeklyMetricsの削除
                deleted_metrics = session.query(WeeklyMetrics).filter(
                    WeeklyMetrics.week_start_date < cutoff_date.date()
                ).delete()
                
                # SyncStatusは削除しない（メンテナンス情報として保持）
                
                # 削除結果を記録
                result = {
                    'deleted_prs': deleted_prs,
                    'deleted_metrics': deleted_metrics
                }
                
                logger.info(f"Cleanup completed: {result}")
                return result
                
        except Exception as e:
            error_msg = f"Failed to cleanup old data: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def get_merged_pull_requests_paginated(self, page: int = 1, page_size: int = 100, 
                                         repo_name: Optional[str] = None) -> Dict[str, Any]:
        """
        ページネーション付きでマージされたプルリクエストデータを取得
        
        Args:
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            repo_name: フィルタ対象のリポジトリ名（Noneの場合は全リポジトリ）
            
        Returns:
            Dict[str, Any]: ページネーション結果
                - data: プルリクエストデータのリスト
                - total_count: 総件数
                - page: 現在のページ番号
                - page_size: ページサイズ
                - has_next_page: 次のページが存在するか
                - has_prev_page: 前のページが存在するか
                
        Raises:
            DatabaseError: データ取得に失敗した場合
        """
        try:
            from .models import PullRequest
            
            logger.debug(f"Querying paginated pull requests: page={page}, page_size={page_size}, repo={repo_name}")
            
            with self.get_session() as session:
                # ベースクエリ
                base_query = session.query(
                    PullRequest.merged_at,
                    PullRequest.author,
                    PullRequest.pr_number,
                    PullRequest.repo_name,
                    PullRequest.title
                ).filter(
                    PullRequest.merged_at.isnot(None)
                )
                
                # リポジトリフィルタ
                if repo_name:
                    base_query = base_query.filter(PullRequest.repo_name == repo_name)
                
                # 総件数を取得
                total_count = base_query.count()
                
                # ページネーション適用
                offset = (page - 1) * page_size
                data_query = base_query.order_by(PullRequest.merged_at.desc()).offset(offset).limit(page_size)
                
                logger.debug(f"Executing paginated query: offset={offset}, limit={page_size}")
                results = data_query.all()
                
                # プルリクエストデータをリスト形式に変換
                pr_data = []
                for merged_at, author, pr_number, repo_name_result, title in results:
                    pr_data.append({
                        'merged_at': merged_at,
                        'author': author,
                        'number': pr_number,
                        'repo_name': repo_name_result,
                        'title': title
                    })
                
                # ページネーション情報を計算
                total_pages = (total_count + page_size - 1) // page_size
                has_next_page = page < total_pages
                has_prev_page = page > 1
                
                result = {
                    'data': pr_data,
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': total_pages,
                    'has_next_page': has_next_page,
                    'has_prev_page': has_prev_page,
                    'showing_from': offset + 1 if pr_data else 0,
                    'showing_to': min(offset + page_size, total_count)
                }
                
                logger.info(f"Retrieved paginated PRs: {len(pr_data)}/{total_count} "
                           f"(page {page}/{total_pages})")
                
                return result
                
        except Exception as e:
            error_msg = f"Failed to retrieve paginated pull requests: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)