"""
Advanced Search Filters
Filter by document, date, file type, etc.
"""
from typing import List, Dict, Optional, Set
from datetime import datetime
from pathlib import Path

class SearchFilters:
    """
    Advanced filtering for search results
    - Filter by document name
    - Filter by file type
    - Filter by date range
    - Filter by relevance threshold
    """
    
    @staticmethod
    def filter_by_documents(
        results: List[Dict],
        document_names: List[str]
    ) -> List[Dict]:
        """
        Filter results by document names
        
        Args:
            results: Search results
            document_names: List of document names to include
            
        Returns:
            Filtered results
        """
        if not document_names:
            return results
        
        return [
            r for r in results
            if r['metadata'].get('source') in document_names
        ]
    
    @staticmethod
    def filter_by_file_type(
        results: List[Dict],
        file_types: List[str]
    ) -> List[Dict]:
        """
        Filter by file extensions
        
        Args:
            results: Search results
            file_types: List of extensions (e.g., ['.pdf', '.docx'])
            
        Returns:
            Filtered results
        """
        if not file_types:
            return results
        
        return [
            r for r in results
            if r['metadata'].get('file_type') in file_types
        ]
    
    @staticmethod
    def filter_by_score(
        results: List[Dict],
        min_score: float = 0.7,
        max_score: float = 1.0
    ) -> List[Dict]:
        """
        Filter by relevance score range
        
        Args:
            results: Search results
            min_score: Minimum score (0-1)
            max_score: Maximum score (0-1)
            
        Returns:
            Filtered results
        """
        return [
            r for r in results
            if min_score <= r['score'] <= max_score
        ]
    
    @staticmethod
    def get_available_documents(results: List[Dict]) -> List[str]:
        """
        Get unique document names from results
        
        Args:
            results: Search results
            
        Returns:
            List of unique document names
        """
        docs = set()
        for r in results:
            doc = r['metadata'].get('source')
            if doc:
                docs.add(doc)
        return sorted(list(docs))
    
    @staticmethod
    def get_available_file_types(results: List[Dict]) -> List[str]:
        """
        Get unique file types from results
        
        Args:
            results: Search results
            
        Returns:
            List of unique file types
        """
        types = set()
        for r in results:
            ftype = r['metadata'].get('file_type')
            if ftype:
                types.add(ftype)
        return sorted(list(types))
    
    @staticmethod
    def group_by_document(results: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group results by source document
        
        Args:
            results: Search results
            
        Returns:
            Dict mapping document name to its results
        """
        grouped = {}
        
        for r in results:
            doc = r['metadata'].get('source', 'Unknown')
            if doc not in grouped:
                grouped[doc] = []
            grouped[doc].append(r)
        
        return grouped
    
    @staticmethod
    def sort_results(
        results: List[Dict],
        sort_by: str = 'score',
        reverse: bool = True
    ) -> List[Dict]:
        """
        Sort results
        
        Args:
            results: Search results
            sort_by: 'score', 'source', 'chunk_id'
            reverse: Descending order
            
        Returns:
            Sorted results
        """
        if sort_by == 'score':
            return sorted(results, key=lambda x: x['score'], reverse=reverse)
        elif sort_by == 'source':
            return sorted(results, key=lambda x: x['metadata'].get('source', ''), reverse=reverse)
        elif sort_by == 'chunk_id':
            return sorted(results, key=lambda x: x['metadata'].get('chunk_id', 0), reverse=reverse)
        else:
            return results
    
    @staticmethod
    def deduplicate_results(
        results: List[Dict],
        similarity_threshold: float = 0.95
    ) -> List[Dict]:
        """
        Remove near-duplicate results
        
        Args:
            results: Search results
            similarity_threshold: Similarity threshold for duplicates
            
        Returns:
            Deduplicated results
        """
        # Simple deduplication by text similarity
        unique_results = []
        seen_texts = set()
        
        for r in results:
            text_key = r['text'][:200]  # First 200 chars
            
            if text_key not in seen_texts:
                unique_results.append(r)
                seen_texts.add(text_key)
        
        return unique_results
    
    @staticmethod
    def highlight_keywords(
        text: str,
        keywords: List[str],
        max_context: int = 200
    ) -> List[Dict]:
        """
        Extract text snippets with keyword highlights
        
        Args:
            text: Full text
            keywords: Keywords to highlight
            max_context: Characters around keyword
            
        Returns:
            List of snippets with positions
        """
        snippets = []
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            pos = 0
            
            while True:
                pos = text_lower.find(keyword_lower, pos)
                if pos == -1:
                    break
                
                # Extract context around keyword
                start = max(0, pos - max_context // 2)
                end = min(len(text), pos + len(keyword) + max_context // 2)
                
                snippet = text[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                
                snippets.append({
                    'text': snippet,
                    'keyword': keyword,
                    'position': pos
                })
                
                pos += len(keyword)
        
        return snippets
    
    @staticmethod
    def get_statistics(results: List[Dict]) -> Dict:
        """
        Get statistics about results
        
        Args:
            results: Search results
            
        Returns:
            Statistics dict
        """
        if not results:
            return {
                'total_results': 0,
                'avg_score': 0,
                'documents': [],
                'file_types': []
            }
        
        scores = [r['score'] for r in results]
        docs = SearchFilters.get_available_documents(results)
        types = SearchFilters.get_available_file_types(results)
        
        grouped = SearchFilters.group_by_document(results)
        doc_stats = [
            {
                'name': doc,
                'count': len(chunks),
                'avg_score': sum(c['score'] for c in chunks) / len(chunks)
            }
            for doc, chunks in grouped.items()
        ]
        
        return {
            'total_results': len(results),
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'unique_documents': len(docs),
            'document_stats': doc_stats,
            'file_types': types
        }
