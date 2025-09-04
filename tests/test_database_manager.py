"""DatabaseManagerのテスト"""
import pytest
import os
import tempfile
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.data_layer.database_manager import DatabaseManager
from src.data_layer.models import Base, PullRequest, WeeklyMetrics, SyncStatus, DatabaseError


class TestDatabaseManager:
    """DatabaseManagerのテストクラス"""
    
    @pytest.fixture
    def temp_db_path(self):
        """一時的なデータベースファイルのパスを作成"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # テスト後にクリーンアップ
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_DatabaseManagerが正常に初期化できる(self, temp_db_path):
        """正常系: DatabaseManagerが正常に初期化できることを確認"""
        manager = DatabaseManager(temp_db_path)
        assert manager is not None
        assert manager.db_path == temp_db_path
    
    def test_DatabaseManagerの初期化でエンジンが作成される(self, temp_db_path):
        """正常系: DatabaseManagerの初期化でSQLAlchemyエンジンが作成されることを確認"""
        manager = DatabaseManager(temp_db_path)
        assert manager.engine is not None
        assert str(manager.engine.url).startswith('sqlite:///')
    
    def test_DatabaseManagerの初期化で無効なパスはエラーになる(self):
        """異常系: 無効なデータベースパスでDatabaseErrorが発生することを確認"""
        invalid_path = "/invalid/path/to/database.db"
        with pytest.raises(DatabaseError):
            DatabaseManager(invalid_path)
    
    def test_initialize_databaseでテーブルが作成される(self, temp_db_path):
        """正常系: initialize_database()でテーブルが作成されることを確認"""
        manager = DatabaseManager(temp_db_path)
        manager.initialize_database()
        
        # データベースファイルが作成されることを確認
        assert os.path.exists(temp_db_path)
        
        # テーブルが作成されることを確認
        with manager.get_session() as session:
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = [row[0] for row in result]
            
            assert 'pull_requests' in table_names
            assert 'weekly_metrics' in table_names
            assert 'sync_status' in table_names
    
    def test_initialize_databaseでインデックスが作成される(self, temp_db_path):
        """正常系: initialize_database()でインデックスが作成されることを確認"""
        manager = DatabaseManager(temp_db_path)
        manager.initialize_database()
        
        with manager.get_session() as session:
            # pull_requestsテーブルのインデックスを確認
            result = session.execute(text("PRAGMA index_list('pull_requests')"))
            indexes = list(result)
            assert len(indexes) > 0
    
    def test_get_sessionがコンテキストマネージャとして動作する(self, temp_db_path):
        """正常系: get_session()がコンテキストマネージャとして動作することを確認"""
        manager = DatabaseManager(temp_db_path)
        manager.initialize_database()
        
        # コンテキストマネージャとして使用可能
        with manager.get_session() as session:
            assert isinstance(session, Session)
            assert session.is_active
        
        # コンテキスト終了後はセッションが閉じられる
        # Note: セッションのクローズ状態の確認は実装によって異なる可能性がある
    
    def test_get_sessionでデータベース操作が実行できる(self, temp_db_path):
        """正常系: get_session()で取得したセッションでデータベース操作ができることを確認"""
        from datetime import datetime, timezone
        
        manager = DatabaseManager(temp_db_path)
        manager.initialize_database()
        
        # データの挿入
        with manager.get_session() as session:
            pr = PullRequest(
                repo_name="test/repo",
                pr_number=123,
                author="test_author",
                title="Test PR",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(pr)
            session.commit()
        
        # データの取得
        with manager.get_session() as session:
            retrieved_pr = session.query(PullRequest).filter_by(repo_name="test/repo").first()
            assert retrieved_pr is not None
            assert retrieved_pr.pr_number == 123
            assert retrieved_pr.author == "test_author"
    
    def test_get_sessionでエラー時にロールバックされる(self, temp_db_path):
        """正常系: get_session()でエラー発生時にトランザクションがロールバックされることを確認"""
        from datetime import datetime, timezone
        from sqlalchemy.exc import IntegrityError
        
        manager = DatabaseManager(temp_db_path)
        manager.initialize_database()
        
        # 最初のPRを作成
        with manager.get_session() as session:
            pr1 = PullRequest(
                repo_name="test/repo",
                pr_number=123,
                author="author1",
                title="First PR",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(pr1)
            session.commit()
        
        # ユニーク制約違反でエラーを発生させる
        try:
            with manager.get_session() as session:
                pr2 = PullRequest(
                    repo_name="test/repo",
                    pr_number=123,  # 同じPR番号でユニーク制約違反
                    author="author2",
                    title="Duplicate PR",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(pr2)
                session.commit()
        except IntegrityError:
            pass  # エラーは期待される
        
        # 元のデータが残っていることを確認
        with manager.get_session() as session:
            prs = session.query(PullRequest).filter_by(repo_name="test/repo").all()
            assert len(prs) == 1
            assert prs[0].author == "author1"
    
    def test_複数のセッションが独立して動作する(self, temp_db_path):
        """正常系: 複数のセッションが独立して動作することを確認"""
        from datetime import datetime, timezone
        
        manager = DatabaseManager(temp_db_path)
        manager.initialize_database()
        
        # 同時に複数のセッションを使用
        with manager.get_session() as session1, manager.get_session() as session2:
            pr1 = PullRequest(
                repo_name="repo1",
                pr_number=1,
                author="author1",
                title="PR1",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            pr2 = PullRequest(
                repo_name="repo2",
                pr_number=2,
                author="author2",
                title="PR2",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            session1.add(pr1)
            session2.add(pr2)
            
            session1.commit()
            session2.commit()
        
        # 両方のデータが保存されていることを確認
        with manager.get_session() as session:
            pr1_retrieved = session.query(PullRequest).filter_by(repo_name="repo1").first()
            pr2_retrieved = session.query(PullRequest).filter_by(repo_name="repo2").first()
            
            assert pr1_retrieved is not None
            assert pr2_retrieved is not None
            assert pr1_retrieved.pr_number == 1
            assert pr2_retrieved.pr_number == 2


class TestDatabaseManagerEdgeCases:
    """DatabaseManagerのエッジケースのテスト"""
    
    def test_存在しないディレクトリのデータベースパス(self):
        """異常系: 存在しないディレクトリのパスでDatabaseErrorが発生することを確認"""
        non_existent_path = "/non/existent/directory/database.db"
        with pytest.raises(DatabaseError, match="Database directory does not exist"):
            DatabaseManager(non_existent_path)
    
    def test_読み取り専用ディレクトリのデータベースパス(self):
        """異常系: 読み取り専用ディレクトリのパスでDatabaseErrorが発生することを確認"""
        # 読み取り専用のテンポラリディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.mkdir(readonly_dir)
            os.chmod(readonly_dir, 0o444)  # 読み取り専用に設定
            
            readonly_path = os.path.join(readonly_dir, "database.db")
            
            try:
                with pytest.raises(DatabaseError, match="Cannot write to database directory"):
                    DatabaseManager(readonly_path)
            finally:
                # クリーンアップのために書き込み権限を復元
                os.chmod(readonly_dir, 0o755)
    
    def test_initialize_database_重複実行(self, temp_db_path=None):
        """正常系: initialize_database()を重複実行してもエラーにならないことを確認"""
        if temp_db_path is None:
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                temp_db_path = f.name
        
        try:
            manager = DatabaseManager(temp_db_path)
            manager.initialize_database()
            
            # 二回目の実行でもエラーにならない
            manager.initialize_database()
            
            # テーブルが正常に存在することを確認
            with manager.get_session() as session:
                result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                table_names = [row[0] for row in result]
                
                assert 'pull_requests' in table_names
                assert 'weekly_metrics' in table_names
                assert 'sync_status' in table_names
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)


class TestDatabaseManagerIntegration:
    """DatabaseManagerの統合テスト"""
    
    def test_全体的なワークフロー(self, temp_db_path=None):
        """統合テスト: DatabaseManagerを使った全体的なワークフローを確認"""
        from datetime import datetime, timezone, date
        
        if temp_db_path is None:
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                temp_db_path = f.name
        
        try:
            # DatabaseManagerの初期化
            manager = DatabaseManager(temp_db_path)
            manager.initialize_database()
            
            # 各モデルのデータを作成
            with manager.get_session() as session:
                # PullRequestの作成
                pr = PullRequest(
                    repo_name="example/repo",
                    pr_number=100,
                    author="developer",
                    title="Feature implementation",
                    merged_at=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                # WeeklyMetricsの作成
                metrics = WeeklyMetrics(
                    week_start_date=date(2024, 1, 1),
                    repo_name="example/repo",
                    pr_count=10,
                    merged_pr_count=8,
                    total_authors=5,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                # SyncStatusの作成
                sync_status = SyncStatus(
                    repo_name="example/repo",
                    last_synced_at=datetime.now(timezone.utc),
                    last_pr_number=100,
                    status="completed",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add_all([pr, metrics, sync_status])
                session.commit()
            
            # データの取得と検証
            with manager.get_session() as session:
                pr_count = session.query(PullRequest).count()
                metrics_count = session.query(WeeklyMetrics).count()
                status_count = session.query(SyncStatus).count()
                
                assert pr_count == 1
                assert metrics_count == 1
                assert status_count == 1
                
                # リポジトリ名による関連データの取得
                repo_pr = session.query(PullRequest).filter_by(repo_name="example/repo").first()
                repo_metrics = session.query(WeeklyMetrics).filter_by(repo_name="example/repo").first()
                repo_status = session.query(SyncStatus).filter_by(repo_name="example/repo").first()
                
                assert repo_pr.pr_number == 100
                assert repo_metrics.pr_count == 10
                assert repo_status.status == "completed"
                
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)