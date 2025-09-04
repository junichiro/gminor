"""SQLAlchemyモデルのテスト"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError

from src.data_layer.models import (
    Base, 
    DatabaseError, 
    PullRequest, 
    WeeklyMetrics, 
    SyncStatus
)


class TestDatabaseModels:
    """データベースモデルのテストクラス"""
    
    @pytest.fixture(scope="function")
    def engine(self):
        """インメモリSQLiteエンジンを作成"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture(scope="function")
    def session(self, engine):
        """テスト用セッションを作成"""
        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()
        yield session
        session.close()
        Session.remove()


class TestPullRequestModel(TestDatabaseModels):
    """PullRequestモデルのテストクラス"""
    
    def test_PullRequestモデルが正常に作成できる(self, session):
        """正常系: PullRequestオブジェクトが作成できることを確認"""
        pr = PullRequest(
            repo_name="test/repo",
            pr_number=123,
            author="test_author",
            title="Test PR Title",
            merged_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(pr)
        session.commit()
        
        # データベースから取得して確認
        saved_pr = session.query(PullRequest).filter_by(repo_name="test/repo", pr_number=123).first()
        assert saved_pr is not None
        assert saved_pr.repo_name == "test/repo"
        assert saved_pr.pr_number == 123
        assert saved_pr.author == "test_author"
        assert saved_pr.title == "Test PR Title"
        assert saved_pr.merged_at is not None
    
    def test_PullRequestの必須フィールドが設定されている(self, session):
        """正常系: 必須フィールドがすべて設定されることを確認"""
        pr = PullRequest(
            repo_name="test/repo",
            pr_number=456,
            author="author2",
            title="Another PR",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(pr)
        session.commit()
        
        saved_pr = session.query(PullRequest).filter_by(pr_number=456).first()
        assert saved_pr.id is not None  # 自動生成される
        assert saved_pr.repo_name == "test/repo"
        assert saved_pr.pr_number == 456
        assert saved_pr.author == "author2"
        assert saved_pr.title == "Another PR"
        assert saved_pr.merged_at is None  # まだマージされていない
    
    def test_PullRequestのユニーク制約が動作する(self, session):
        """異常系: (repo_name, pr_number)のユニーク制約が動作することを確認"""
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
        
        # 同じrepo_name + pr_numberの組み合わせで別のPRを作成
        pr2 = PullRequest(
            repo_name="test/repo",
            pr_number=123,  # 同じPR番号
            author="author2",
            title="Duplicate PR",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(pr2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_PullRequestのテーブル名が正しい(self, engine):
        """正常系: テーブル名が'pull_requests'であることを確認"""
        # テーブル一覧を取得
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            table_names = [row[0] for row in result]
        
        assert 'pull_requests' in table_names
    
    def test_PullRequestのインデックスが設定されている(self, engine):
        """正常系: 適切なインデックスが設定されていることを確認"""
        # SQLiteの場合、インデックス情報を取得
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA index_list('pull_requests');"))
            indexes = list(result)
        
        # ユニークインデックスが存在することを確認
        assert len(indexes) > 0
    
    def test_PullRequest_is_mergedプロパティ(self, session):
        """正常系: is_mergedプロパティが正しく動作することを確認"""
        now = datetime.now(timezone.utc)
        
        # merged_atがある場合
        pr_merged = PullRequest(
            repo_name="test/repo", 
            pr_number=1, 
            author="test", 
            title="Merged PR",
            created_at=now,
            updated_at=now,
            merged_at=now
        )
        assert pr_merged.is_merged is True
        
        # merged_atがない場合
        pr_not_merged = PullRequest(
            repo_name="test/repo", 
            pr_number=2, 
            author="test", 
            title="Not merged PR",
            created_at=now,
            updated_at=now,
            merged_at=None
        )
        assert pr_not_merged.is_merged is False
    
    def test_PullRequest_get_full_identifierメソッド(self, session):
        """正常系: get_full_identifierメソッドが正しく動作することを確認"""
        now = datetime.now(timezone.utc)
        pr = PullRequest(
            repo_name="owner/repository",
            pr_number=123,
            author="test_author",
            title="Test PR",
            created_at=now,
            updated_at=now
        )
        
        expected = "owner/repository#123"
        assert pr.get_full_identifier() == expected


class TestWeeklyMetricsModel(TestDatabaseModels):
    """WeeklyMetricsモデルのテストクラス"""
    
    def test_WeeklyMetricsモデルが正常に作成できる(self, session):
        """正常系: WeeklyMetricsオブジェクトが作成できることを確認"""
        metrics = WeeklyMetrics(
            week_start_date=datetime(2024, 1, 1).date(),
            repo_name="test/repo",
            pr_count=5,
            merged_pr_count=3,
            total_authors=2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(metrics)
        session.commit()
        
        saved_metrics = session.query(WeeklyMetrics).first()
        assert saved_metrics is not None
        assert saved_metrics.week_start_date.year == 2024
        assert saved_metrics.repo_name == "test/repo"
        assert saved_metrics.pr_count == 5
        assert saved_metrics.merged_pr_count == 3
        assert saved_metrics.total_authors == 2
    
    def test_WeeklyMetricsのユニーク制約が動作する(self, session):
        """異常系: (week_start_date, repo_name)のユニーク制約が動作することを確認"""
        week_date = datetime(2024, 1, 1).date()
        
        metrics1 = WeeklyMetrics(
            week_start_date=week_date,
            repo_name="test/repo",
            pr_count=5,
            merged_pr_count=3,
            total_authors=2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(metrics1)
        session.commit()
        
        # 同じ週・同じリポジトリで別のメトリクスを作成
        metrics2 = WeeklyMetrics(
            week_start_date=week_date,  # 同じ週
            repo_name="test/repo",     # 同じリポジトリ
            pr_count=10,
            merged_pr_count=8,
            total_authors=4,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(metrics2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_WeeklyMetricsのテーブル名が正しい(self, engine):
        """正常系: テーブル名が'weekly_metrics'であることを確認"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            table_names = [row[0] for row in result]
        
        assert 'weekly_metrics' in table_names
    
    def test_WeeklyMetricsのバリデーションが負の値を拒否する(self):
        """異常系: pr_countに負の値を設定するとValueErrorが発生することを確認"""
        with pytest.raises(ValueError, match="pr_count must be non-negative"):
            WeeklyMetrics(
                week_start_date=datetime(2024, 1, 1).date(),
                repo_name="test/repo",
                pr_count=-1,
                merged_pr_count=5,
                total_authors=2,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
    
    def test_WeeklyMetricsのmerge_rateプロパティ(self):
        """正常系: merge_rateプロパティが正しく計算されることを確認"""
        now = datetime.now(timezone.utc)
        
        # PR数が0の場合
        metrics_zero = WeeklyMetrics(
            week_start_date=datetime(2024, 1, 1).date(),
            repo_name="test/repo",
            pr_count=0,
            merged_pr_count=0,
            total_authors=0,
            created_at=now,
            updated_at=now
        )
        assert metrics_zero.merge_rate == 0.0
        
        # 正常な計算
        metrics_normal = WeeklyMetrics(
            week_start_date=datetime(2024, 1, 1).date(),
            repo_name="test/repo",
            pr_count=10,
            merged_pr_count=8,
            total_authors=3,
            created_at=now,
            updated_at=now
        )
        assert metrics_normal.merge_rate == 0.8
    
    def test_WeeklyMetricsのweek_end_dateプロパティ(self):
        """正常系: week_end_dateプロパティが正しく計算されることを確認"""
        now = datetime.now(timezone.utc)
        metrics = WeeklyMetrics(
            week_start_date=datetime(2024, 1, 1).date(),  # 月曜日
            repo_name="test/repo",
            pr_count=5,
            merged_pr_count=3,
            total_authors=2,
            created_at=now,
            updated_at=now
        )
        
        expected_end_date = datetime(2024, 1, 7).date()  # 日曜日
        assert metrics.week_end_date == expected_end_date
    
    def test_WeeklyMetricsのget_week_range_strメソッド(self):
        """正常系: get_week_range_strメソッドが正しい文字列を返すことを確認"""
        now = datetime.now(timezone.utc)
        metrics = WeeklyMetrics(
            week_start_date=datetime(2024, 1, 1).date(),
            repo_name="test/repo",
            pr_count=5,
            merged_pr_count=3,
            total_authors=2,
            created_at=now,
            updated_at=now
        )
        
        expected = "2024-01-01 - 2024-01-07"
        assert metrics.get_week_range_str() == expected


class TestSyncStatusModel(TestDatabaseModels):
    """SyncStatusモデルのテストクラス"""
    
    def test_SyncStatusモデルが正常に作成できる(self, session):
        """正常系: SyncStatusオブジェクトが作成できることを確認"""
        sync_status = SyncStatus(
            repo_name="test/repo",
            last_synced_at=datetime.now(timezone.utc),
            last_pr_number=150,
            status="completed",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(sync_status)
        session.commit()
        
        saved_status = session.query(SyncStatus).first()
        assert saved_status is not None
        assert saved_status.repo_name == "test/repo"
        assert saved_status.last_pr_number == 150
        assert saved_status.status == "completed"
        assert saved_status.last_synced_at is not None
    
    def test_SyncStatusのリポジトリ名ユニーク制約が動作する(self, session):
        """異常系: repo_nameのユニーク制約が動作することを確認"""
        status1 = SyncStatus(
            repo_name="test/repo",
            last_synced_at=datetime.now(timezone.utc),
            last_pr_number=100,
            status="in_progress",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(status1)
        session.commit()
        
        # 同じリポジトリで別のSyncStatusを作成
        status2 = SyncStatus(
            repo_name="test/repo",  # 同じリポジトリ名
            last_synced_at=datetime.now(timezone.utc),
            last_pr_number=200,
            status="completed",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(status2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_SyncStatusのテーブル名が正しい(self, engine):
        """正常系: テーブル名が'sync_status'であることを確認"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            table_names = [row[0] for row in result]
        
        assert 'sync_status' in table_names
    
    def test_SyncStatusのバリデーションが無効なステータスを拒否する(self):
        """異常系: statusに無効な値を設定するとValueErrorが発生することを確認"""
        with pytest.raises(ValueError, match="Status must be one of"):
            SyncStatus(
                repo_name="test/repo",
                status="invalid_status",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
    
    def test_SyncStatusのis_completedメソッド(self):
        """正常系: is_completedメソッドが正しく動作することを確認"""
        now = datetime.now(timezone.utc)
        
        # 完了状態
        sync_completed = SyncStatus(
            repo_name="test/repo",
            status="completed",
            created_at=now,
            updated_at=now
        )
        assert sync_completed.is_completed() is True
        
        # 未完了状態
        sync_pending = SyncStatus(
            repo_name="test/repo",
            status="pending",
            created_at=now,
            updated_at=now
        )
        assert sync_pending.is_completed() is False
    
    def test_SyncStatusのis_errorメソッド(self):
        """正常系: is_errorメソッドが正しく動作することを確認"""
        now = datetime.now(timezone.utc)
        
        # エラー状態
        sync_error = SyncStatus(
            repo_name="test/repo",
            status="error",
            error_message="Test error",
            created_at=now,
            updated_at=now
        )
        assert sync_error.is_error() is True
        
        # 正常状態
        sync_normal = SyncStatus(
            repo_name="test/repo",
            status="completed",
            created_at=now,
            updated_at=now
        )
        assert sync_normal.is_error() is False
    
    def test_SyncStatusのmark_completedメソッド(self):
        """正常系: mark_completedメソッドが正しく動作することを確認"""
        now = datetime.now(timezone.utc)
        sync = SyncStatus(
            repo_name="test/repo",
            status="in_progress",
            created_at=now,
            updated_at=now
        )
        
        # 完了マーク（PR番号なし）
        sync.mark_completed()
        assert sync.status == "completed"
        assert sync.error_message is None
        assert sync.last_synced_at is not None
        assert sync.updated_at is not None
        
        # 完了マーク（PR番号あり）
        sync.mark_completed(last_pr_number=150)
        assert sync.last_pr_number == 150
    
    def test_SyncStatusのmark_errorメソッド(self):
        """正常系: mark_errorメソッドが正しく動作することを確認"""
        now = datetime.now(timezone.utc)
        sync = SyncStatus(
            repo_name="test/repo",
            status="in_progress",
            created_at=now,
            updated_at=now
        )
        
        error_msg = "Connection timeout"
        sync.mark_error(error_msg)
        
        assert sync.status == "error"
        assert sync.error_message == error_msg
        assert sync.updated_at is not None


class TestModelRelationships(TestDatabaseModels):
    """モデル間のリレーションシップのテストクラス"""
    
    def test_リレーションシップが正常に動作する(self, session):
        """正常系: モデル間のリレーションシップが正常に動作することを確認"""
        # PullRequestを作成
        pr = PullRequest(
            repo_name="test/repo",
            pr_number=123,
            author="test_author",
            title="Test PR",
            merged_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # WeeklyMetricsを作成
        metrics = WeeklyMetrics(
            week_start_date=datetime(2024, 1, 1).date(),
            repo_name="test/repo",
            pr_count=1,
            merged_pr_count=1,
            total_authors=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # SyncStatusを作成
        sync_status = SyncStatus(
            repo_name="test/repo",
            last_synced_at=datetime.now(timezone.utc),
            last_pr_number=123,
            status="completed",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add_all([pr, metrics, sync_status])
        session.commit()
        
        # リポジトリ名で関連するデータを取得できることを確認
        repo_prs = session.query(PullRequest).filter_by(repo_name="test/repo").all()
        repo_metrics = session.query(WeeklyMetrics).filter_by(repo_name="test/repo").all()
        repo_status = session.query(SyncStatus).filter_by(repo_name="test/repo").first()
        
        assert len(repo_prs) == 1
        assert len(repo_metrics) == 1
        assert repo_status is not None
        
        # すべて同じリポジトリ名を持つことを確認
        assert repo_prs[0].repo_name == "test/repo"
        assert repo_metrics[0].repo_name == "test/repo"
        assert repo_status.repo_name == "test/repo"


class TestDatabaseError:
    """DatabaseError例外のテスト"""
    
    def test_DatabaseErrorが正常に発生する(self):
        """正常系: DatabaseError例外が正常に発生することを確認"""
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("テストエラー")
        
        assert "テストエラー" in str(exc_info.value)
        assert isinstance(exc_info.value, Exception)
    
    def test_DatabaseErrorに詳細メッセージを設定できる(self):
        """正常系: DatabaseErrorに詳細なエラーメッセージを設定できることを確認"""
        error_msg = "データベース接続に失敗しました: connection timeout"
        
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError(error_msg)
        
        assert error_msg == str(exc_info.value)