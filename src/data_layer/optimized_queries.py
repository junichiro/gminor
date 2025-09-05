"""最適化されたデータベースクエリ - パフォーマンス向上のためのクエリ最適化"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from .models import PullRequest, WeeklyMetrics

logger = logging.getLogger(__name__)


class OptimizedQueries:
    """パフォーマンス最適化されたデータベースクエリクラス"""
    
    def __init__(self, session: Session):
        """
        OptimizedQueriesを初期化
        
        Args:
            session: SQLAlchemyセッション
        """
        self.session = session
        logger.info("OptimizedQueries initialized")
    
    def get_prs_by_date_range_optimized(self, repo_name: str, start_date: datetime, 
                                      end_date: datetime) -> Dict[str, Any]:
        """
        日付範囲でPRを効率的に取得（インデックス最適化）
        
        Args:
            repo_name: リポジトリ名
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            Dict[str, Any]: クエリ結果と実行情報
        """
        start_time = time.time()
        
        logger.debug(f"Executing optimized PR query for {repo_name}: {start_date} to {end_date}")
        
        try:
            # インデックスを効率的に使用するクエリ
            query = self.session.query(PullRequest).filter(
                PullRequest.repo_name == repo_name,
                PullRequest.merged_at >= start_date,
                PullRequest.merged_at <= end_date
            ).order_by(PullRequest.merged_at)
            
            # クエリプランの情報を取得（SQLite用）
            explain_query = f"""
            EXPLAIN QUERY PLAN 
            SELECT * FROM pull_requests 
            WHERE repo_name = '{repo_name}' 
            AND merged_at >= '{start_date}' 
            AND merged_at <= '{end_date}'
            ORDER BY merged_at
            """
            
            explain_result = self.session.execute(text(explain_query)).fetchall()
            
            # 実際のデータを取得
            results = query.all()
            
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            # インデックス使用の確認
            uses_index = any('INDEX' in str(row) for row in explain_result)
            
            result = {
                'data': [
                    {
                        'pr_number': pr.pr_number,
                        'author': pr.author,
                        'title': pr.title,
                        'merged_at': pr.merged_at,
                        'created_at': pr.created_at
                    }
                    for pr in results
                ],
                'count': len(results),
                'execution_time_ms': execution_time_ms,
                'query_plan': {
                    'uses_index': uses_index,
                    'plan_details': [str(row) for row in explain_result]
                },
                'optimization_applied': True
            }
            
            logger.info(f"Optimized query executed: {len(results)} results in {execution_time_ms:.2f}ms, "
                       f"uses_index: {uses_index}")
            
            return result
            
        except Exception as e:
            logger.error(f"Optimized query failed: {e}")
            return {
                'data': [],
                'count': 0,
                'execution_time_ms': (time.time() - start_time) * 1000,
                'error': str(e),
                'query_plan': {'uses_index': False}
            }
    
    def get_aggregated_metrics_optimized(self, repo_name: str, limit: int = 100) -> Dict[str, Any]:
        """
        集計メトリクスを効率的に取得
        
        Args:
            repo_name: リポジトリ名
            limit: 取得件数制限
            
        Returns:
            Dict[str, Any]: 集計結果
        """
        start_time = time.time()
        
        logger.debug(f"Executing optimized aggregation query for {repo_name}")
        
        try:
            # 効率的な集計クエリ
            query = self.session.query(
                PullRequest.author,
                func.count(PullRequest.pr_number).label('pr_count'),
                func.min(PullRequest.merged_at).label('first_pr'),
                func.max(PullRequest.merged_at).label('last_pr')
            ).filter(
                PullRequest.repo_name == repo_name,
                PullRequest.merged_at.isnot(None)
            ).group_by(PullRequest.author).order_by(
                func.count(PullRequest.pr_number).desc()
            ).limit(limit)
            
            results = query.all()
            
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            aggregated_data = [
                {
                    'author': result.author,
                    'pr_count': result.pr_count,
                    'first_pr': result.first_pr,
                    'last_pr': result.last_pr
                }
                for result in results
            ]
            
            result = {
                'data': aggregated_data,
                'count': len(aggregated_data),
                'execution_time_ms': execution_time_ms,
                'optimization_applied': True,
                'total_prs': sum(item['pr_count'] for item in aggregated_data)
            }
            
            logger.info(f"Optimized aggregation query executed: {len(results)} authors in {execution_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Optimized aggregation query failed: {e}")
            return {
                'data': [],
                'count': 0,
                'execution_time_ms': (time.time() - start_time) * 1000,
                'error': str(e)
            }
    
    def bulk_insert_optimized(self, pr_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        最適化された一括挿入
        
        Args:
            pr_data_list: PR データのリスト
            
        Returns:
            Dict[str, Any]: 挿入結果
        """
        start_time = time.time()
        
        if not pr_data_list:
            return {
                'inserted_count': 0,
                'execution_time_ms': 0,
                'status': 'success'
            }
        
        logger.debug(f"Executing optimized bulk insert for {len(pr_data_list)} PRs")
        
        try:
            # 一括挿入用のデータ準備
            insert_data = []
            for pr_data in pr_data_list:
                insert_data.append({
                    'repo_name': pr_data['repo_name'],
                    'pr_number': pr_data['pr_number'],
                    'author': pr_data['author'],
                    'title': pr_data['title'],
                    'merged_at': pr_data['merged_at'],
                    'created_at': pr_data['created_at'],
                    'updated_at': pr_data['updated_at']
                })
            
            # 一括挿入実行
            self.session.bulk_insert_mappings(PullRequest, insert_data)
            self.session.commit()
            
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            result = {
                'inserted_count': len(pr_data_list),
                'execution_time_ms': execution_time_ms,
                'status': 'success',
                'optimization_applied': True,
                'throughput_per_second': len(pr_data_list) / (execution_time_ms / 1000) if execution_time_ms > 0 else 0
            }
            
            logger.info(f"Optimized bulk insert completed: {len(pr_data_list)} records in {execution_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Optimized bulk insert failed: {e}")
            self.session.rollback()
            return {
                'inserted_count': 0,
                'execution_time_ms': (time.time() - start_time) * 1000,
                'status': 'error',
                'error': str(e)
            }
    
    def analyze_table_performance(self, table_name: str) -> Dict[str, Any]:
        """
        テーブルのパフォーマンス分析
        
        Args:
            table_name: 分析対象のテーブル名
            
        Returns:
            Dict[str, Any]: パフォーマンス分析結果
        """
        start_time = time.time()
        
        logger.debug(f"Analyzing table performance: {table_name}")
        
        try:
            # テーブル情報を取得
            table_info_query = f"PRAGMA table_info({table_name})"
            table_info = self.session.execute(text(table_info_query)).fetchall()
            
            # インデックス情報を取得
            index_info_query = f"PRAGMA index_list({table_name})"
            index_info = self.session.execute(text(index_info_query)).fetchall()
            
            # テーブル統計を取得
            stats_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            stats_result = self.session.execute(text(stats_query)).fetchone()
            
            end_time = time.time()
            analysis_time_ms = (end_time - start_time) * 1000
            
            result = {
                'table_name': table_name,
                'row_count': stats_result[0] if stats_result else 0,
                'columns': [
                    {
                        'name': col[1],
                        'type': col[2],
                        'not_null': bool(col[3]),
                        'primary_key': bool(col[5])
                    }
                    for col in table_info
                ],
                'indexes': [
                    {
                        'name': idx[1],
                        'unique': bool(idx[2])
                    }
                    for idx in index_info
                ],
                'analysis_time_ms': analysis_time_ms,
                'performance_score': self._calculate_performance_score(len(index_info), stats_result[0] if stats_result else 0)
            }
            
            logger.info(f"Table performance analysis completed: {table_name} in {analysis_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Table performance analysis failed: {e}")
            return {
                'table_name': table_name,
                'error': str(e),
                'analysis_time_ms': (time.time() - start_time) * 1000
            }
    
    def _calculate_performance_score(self, index_count: int, row_count: int) -> float:
        """
        パフォーマンススコアを計算
        
        Args:
            index_count: インデックス数
            row_count: レコード数
            
        Returns:
            float: パフォーマンススコア（0-100）
        """
        # 簡単なスコアリング アルゴリズム
        base_score = 50.0
        
        # インデックスがあるとスコアが上がる
        index_bonus = min(index_count * 10, 30)
        
        # 大量データでインデックスが少ないとスコアが下がる
        if row_count > 10000 and index_count < 3:
            large_data_penalty = -20
        else:
            large_data_penalty = 0
        
        score = base_score + index_bonus + large_data_penalty
        return max(0, min(100, score))