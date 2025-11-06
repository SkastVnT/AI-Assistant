"""
Analytics and Usage Tracking
Track queries, document usage, performance metrics
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, Counter

class AnalyticsTracker:
    """
    Track and analyze RAG system usage
    - Query statistics
    - Document popularity
    - Performance metrics
    - User behavior patterns
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.analytics_file = data_dir / "analytics.json"
        self.analytics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing analytics
        self.data = self._load_analytics()
    
    def _load_analytics(self) -> Dict:
        """Load analytics from file"""
        if self.analytics_file.exists():
            try:
                with open(self.analytics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._create_empty_analytics()
        return self._create_empty_analytics()
    
    def _create_empty_analytics(self) -> Dict:
        """Create empty analytics structure"""
        return {
            'queries': [],
            'documents': {},
            'performance': {
                'total_queries': 0,
                'search_queries': 0,
                'rag_queries': 0,
                'failed_queries': 0,
                'avg_response_time': 0
            },
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_analytics(self):
        """Save analytics to file"""
        self.data['last_updated'] = datetime.now().isoformat()
        with open(self.analytics_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def track_query(
        self,
        query: str,
        mode: str,  # 'search' or 'rag'
        results_count: int,
        response_time: float,
        success: bool = True,
        documents_used: Optional[List[str]] = None
    ):
        """
        Track a single query
        
        Args:
            query: User query
            mode: 'search' or 'rag'
            results_count: Number of results returned
            response_time: Response time in seconds
            success: Whether query succeeded
            documents_used: List of documents used in results
        """
        query_data = {
            'query': query,
            'mode': mode,
            'results_count': results_count,
            'response_time': response_time,
            'success': success,
            'documents_used': documents_used or [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to queries list (keep last 1000)
        self.data['queries'].append(query_data)
        if len(self.data['queries']) > 1000:
            self.data['queries'] = self.data['queries'][-1000:]
        
        # Update performance metrics
        perf = self.data['performance']
        perf['total_queries'] += 1
        
        if mode == 'search':
            perf['search_queries'] += 1
        elif mode == 'rag':
            perf['rag_queries'] += 1
        
        if not success:
            perf['failed_queries'] += 1
        
        # Update avg response time
        total = perf['total_queries']
        perf['avg_response_time'] = (
            perf['avg_response_time'] * (total - 1) + response_time
        ) / total
        
        # Track document usage
        for doc in (documents_used or []):
            if doc not in self.data['documents']:
                self.data['documents'][doc] = {
                    'name': doc,
                    'queries': 0,
                    'first_used': datetime.now().isoformat(),
                    'last_used': datetime.now().isoformat()
                }
            
            self.data['documents'][doc]['queries'] += 1
            self.data['documents'][doc]['last_used'] = datetime.now().isoformat()
        
        self._save_analytics()
    
    def get_popular_queries(self, top_n: int = 10) -> List[Dict]:
        """
        Get most popular queries
        
        Args:
            top_n: Number of top queries
            
        Returns:
            List of queries with counts
        """
        query_counter = Counter()
        
        for q in self.data['queries']:
            if q['success']:
                query_counter[q['query']] += 1
        
        return [
            {'query': query, 'count': count}
            for query, count in query_counter.most_common(top_n)
        ]
    
    def get_popular_documents(self, top_n: int = 10) -> List[Dict]:
        """
        Get most used documents
        
        Args:
            top_n: Number of top documents
            
        Returns:
            List of documents with usage counts
        """
        docs = sorted(
            self.data['documents'].values(),
            key=lambda x: x['queries'],
            reverse=True
        )
        return docs[:top_n]
    
    def get_query_trends(
        self,
        period: str = 'day'  # 'hour', 'day', 'week'
    ) -> Dict:
        """
        Get query trends over time
        
        Args:
            period: Time period for grouping
            
        Returns:
            Dict with time periods and query counts
        """
        trends = defaultdict(lambda: {'search': 0, 'rag': 0, 'total': 0})
        
        for q in self.data['queries']:
            if not q['success']:
                continue
            
            timestamp = datetime.fromisoformat(q['timestamp'])
            
            if period == 'hour':
                key = timestamp.strftime('%Y-%m-%d %H:00')
            elif period == 'day':
                key = timestamp.strftime('%Y-%m-%d')
            elif period == 'week':
                key = timestamp.strftime('%Y-W%W')
            else:
                key = timestamp.strftime('%Y-%m-%d')
            
            trends[key]['total'] += 1
            trends[key][q['mode']] += 1
        
        return dict(sorted(trends.items()))
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return self.data['performance'].copy()
    
    def get_recent_queries(self, count: int = 20) -> List[Dict]:
        """
        Get recent queries
        
        Args:
            count: Number of recent queries
            
        Returns:
            List of recent queries
        """
        return self.data['queries'][-count:][::-1]  # Reverse for newest first
    
    def get_query_by_mode(self) -> Dict:
        """Get query count by mode"""
        search_count = sum(1 for q in self.data['queries'] if q['mode'] == 'search')
        rag_count = sum(1 for q in self.data['queries'] if q['mode'] == 'rag')
        
        return {
            'search': search_count,
            'rag': rag_count,
            'total': search_count + rag_count
        }
    
    def get_success_rate(self) -> Dict:
        """Get query success rate"""
        total = len(self.data['queries'])
        if total == 0:
            return {'rate': 1.0, 'successful': 0, 'failed': 0}
        
        successful = sum(1 for q in self.data['queries'] if q['success'])
        failed = total - successful
        
        return {
            'rate': successful / total,
            'successful': successful,
            'failed': failed,
            'total': total
        }
    
    def get_avg_results_per_query(self) -> float:
        """Get average number of results per query"""
        queries = [q for q in self.data['queries'] if q['success']]
        if not queries:
            return 0
        
        return sum(q['results_count'] for q in queries) / len(queries)
    
    def get_dashboard_data(self) -> Dict:
        """
        Get complete dashboard data
        
        Returns:
            Dict with all analytics
        """
        return {
            'performance': self.get_performance_stats(),
            'query_by_mode': self.get_query_by_mode(),
            'success_rate': self.get_success_rate(),
            'avg_results': self.get_avg_results_per_query(),
            'popular_queries': self.get_popular_queries(10),
            'popular_documents': self.get_popular_documents(10),
            'recent_queries': self.get_recent_queries(10),
            'trends': self.get_query_trends('day')
        }
    
    def clear_old_data(self, days: int = 30):
        """
        Clear queries older than specified days
        
        Args:
            days: Keep data for last N days
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        self.data['queries'] = [
            q for q in self.data['queries']
            if datetime.fromisoformat(q['timestamp']) > cutoff
        ]
        
        self._save_analytics()
    
    def export_report(self, output_file: Path):
        """
        Export analytics report
        
        Args:
            output_file: Output file path
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'period': {
                'start': self.data['created_at'],
                'end': self.data['last_updated']
            },
            'summary': self.get_dashboard_data()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


# Global instance
_analytics_tracker = None

def get_analytics_tracker(data_dir: Optional[Path] = None) -> AnalyticsTracker:
    """Get global analytics tracker instance"""
    global _analytics_tracker
    
    if _analytics_tracker is None:
        if data_dir is None:
            from .config import settings
            data_dir = settings.DATA_DIR
        _analytics_tracker = AnalyticsTracker(data_dir)
    
    return _analytics_tracker
