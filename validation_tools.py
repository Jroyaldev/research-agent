"""
Anti-Hallucination Tools and Citation Validation
Provides robust citation checking and hallucination detection
"""

import re
import requests
from typing import Dict, List, Any, Optional, Tuple
import json
from urllib.parse import urlparse
import sqlite3
import logging
from datetime import datetime, timezone
from contextlib import contextmanager
import threading
from functools import wraps

class CitationValidator:
    """Validates citations and detects hallucinations in research output with proper resource management"""
    
    def __init__(self, db_path: str = "research_tasks.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._db_lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database with proper error handling"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS validation_results (
                        id TEXT PRIMARY KEY,
                        graph_id TEXT,
                        validation_data TEXT,
                        created_at TEXT,
                        UNIQUE(graph_id)
                    )
                ''')
                conn.commit()
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper resource management"""
        conn = None
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.execute('PRAGMA journal_mode=WAL')  # Better concurrency
                conn.execute('PRAGMA synchronous=NORMAL')  # Performance optimization
                yield conn
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected database error: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
        
    def extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from research text"""
        citations = []
        
        # Pattern 1: Academic citations with years
        # e.g., (Smith, 2023), Smith (2023), Smith et al. (2023)
        citation_patterns = [
            r'\(([^)]+\d{4})\)',  # (Author, Year)
            r'(\w+(?:\s+et\s+al\.?)?\s*\(\d{4}\))',  # Author (Year)
            r'(\w+(?:\s+and\s+\w+)?\s*\(\d{4}\))',  # Author and Author (Year)
        ]
        
        for pattern in citation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                citation_text = match.group(1)
                citations.append({
                    'type': 'citation',
                    'text': citation_text,
                    'start': match.start(),
                    'end': match.end(),
                    'validated': False,
                    'source_url': None
                })
        
        # Pattern 2: URL citations
        url_pattern = r'https?://[^\s\)\]]+'
        urls = re.finditer(url_pattern, text)
        for url_match in urls:
            url = url_match.group(0)
            citations.append({
                'type': 'url',
                'text': url,
                'start': url_match.start(),
                'end': url_match.end(),
                'validated': False,
                'source_url': url
            })
        
        return citations
    
    def _validate_url_format(self, url: str) -> bool:
        """Basic URL format validation"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
        except Exception:
            return False
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate if URL is accessible with proper input validation and error handling"""
        
        # Input validation
        if not url or not isinstance(url, str):
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': 'Invalid URL format'
            }
        
        # Basic format validation
        if not self._validate_url_format(url):
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': 'Invalid URL format'
            }
        
        # Length check
        if len(url) > 2048:
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': 'URL too long'
            }
        
        try:
            # Use session for connection reuse
            with requests.Session() as session:
                session.headers.update({
                    'User-Agent': 'Research-Agent-Validator/1.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                })
                
                response = session.head(
                    url, 
                    timeout=15.0, 
                    allow_redirects=True,
                    verify=True  # SSL verification
                )
                
                return {
                    'url': url,
                    'accessible': response.status_code == 200,
                    'status_code': response.status_code,
                    'final_url': response.url,
                    'content_type': response.headers.get('content-type', 'unknown'),
                    'error': None
                }
                
        except requests.exceptions.Timeout:
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': 'Request timeout'
            }
        except requests.exceptions.ConnectionError:
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': 'Connection error'
            }
        except requests.exceptions.SSLError:
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': 'SSL certificate error'
            }
        except requests.RequestException as e:
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': str(e)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error validating URL {url}: {str(e)}", exc_info=True)
            return {
                'url': url,
                'accessible': False,
                'status_code': None,
                'final_url': url,
                'content_type': 'unknown',
                'error': f'Validation error: {str(e)}'
            }
    
    def validate_citation_against_sources(self, citation: Dict[str, Any], 
                                        sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate citation against actual sources"""
        citation_text = citation['text']
        
        # Check if citation matches any source
        for source in sources:
            source_title = source.get('title', '').lower()
            source_url = source.get('url', '')
            
            # Check if citation text contains source title keywords
            title_words = re.findall(r'\w+', source_title)
            citation_words = re.findall(r'\w+', citation_text.lower())
            
            # Simple matching - at least 2 words match
            matching_words = set(title_words) & set(citation_words)
            if len(matching_words) >= 2:
                return {
                    'citation': citation,
                    'validated': True,
                    'source': source,
                    'match_type': 'title_match',
                    'confidence': min(len(matching_words) / len(title_words), 1.0)
                }
        
        return {
            'citation': citation,
            'validated': False,
            'source': None,
            'match_type': 'no_match',
            'confidence': 0.0
        }
    
    def detect_hallucinations(self, content: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect potential hallucinations in research content"""
        
        # Extract claims that should be supported by sources
        claims = self._extract_claims(content)
        
        # Validate citations
        citations = self.extract_citations(content)
        validated_citations = []
        
        for citation in citations:
            if citation['type'] == 'url':
                url_validation = self.validate_url(citation['text'])
                citation['validated'] = url_validation['accessible']
                citation['url_validation'] = url_validation
            else:
                # Validate against provided sources
                validation = self.validate_citation_against_sources(citation, sources)
                citation.update(validation)
            
            validated_citations.append(citation)
        
        # Check for unsupported claims
        unsupported_claims = []
        for claim in claims:
            has_support = self._claim_has_citation_support(claim, validated_citations)
            if not has_support:
                unsupported_claims.append(claim)
        
        # Calculate hallucination risk score
        risk_score = self._calculate_hallucination_risk(
            validated_citations, unsupported_claims, len(claims)
        )
        
        return {
            'content': content,
            'citations': validated_citations,
            'claims': claims,
            'unsupported_claims': unsupported_claims,
            'hallucination_risk': risk_score,
            'validation_passed': risk_score < 0.3,  # Threshold
            'recommendations': self._generate_recommendations(validated_citations, unsupported_claims)
        }
    
    def _extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """Extract factual claims from text that should be cited"""
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip short fragments
                continue
            
            # Look for factual statements
            factual_patterns = [
                r'\b(is|was|are|were|has|had|shows|demonstrates|proves|indicates)\b.*\b(that|how|why)\b',
                r'\baccording to\b',
                r'\bstudies?\s+show\b',
                r'\bresearch\s+(indicates|shows|demonstrates)\b',
                r'\b\d{4}\b.*\bfound\b',  # Year + found
            ]
            
            for pattern in factual_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append({
                        'text': sentence,
                        'type': 'factual_claim',
                        'requires_citation': True
                    })
                    break
        
        return claims
    
    def _claim_has_citation_support(self, claim: Dict[str, Any], 
                                  citations: List[Dict[str, Any]]) -> bool:
        """Check if a claim has supporting citations"""
        claim_text = claim['text'].lower()
        
        for citation in citations:
            if citation.get('validated', False):
                # Check if citation is close to the claim
                citation_pos = citation.get('start', 0)
                claim_pos = claim.get('position', 0)
                
                # Consider citation valid if within 500 characters
                if abs(citation_pos - claim_pos) < 500:
                    return True
        
        return False
    
    def _calculate_hallucination_risk(self, citations: List[Dict[str, Any]], 
                                    unsupported_claims: List[Dict[str, Any]], 
                                    total_claims: int) -> float:
        """Calculate hallucination risk score (0-1)"""
        
        if total_claims == 0:
            return 0.0
        
        # Factors:
        # 1. Ratio of unsupported claims
        unsupported_ratio = len(unsupported_claims) / max(total_claims, 1)
        
        # 2. Ratio of invalid citations
        invalid_citations = [c for c in citations if not c.get('validated', False)]
        citation_invalid_ratio = len(invalid_citations) / max(len(citations), 1)
        
        # 3. Overall citation coverage
        citation_coverage = len(citations) / max(total_claims, 1)
        
        # Weighted risk calculation
        risk = (unsupported_ratio * 0.5 + 
               citation_invalid_ratio * 0.3 + 
               max(1 - citation_coverage, 0) * 0.2)
        
        return min(risk, 1.0)
    
    def _generate_recommendations(self, citations: List[Dict[str, Any]], 
                                unsupported_claims: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for improving citation quality"""
        recommendations = []
        
        invalid_urls = [c for c in citations if c.get('type') == 'url' and not c.get('validated', False)]
        if invalid_urls:
            recommendations.append(f"Fix {len(invalid_urls)} invalid URLs")
        
        if unsupported_claims:
            recommendations.append(f"Add citations for {len(unsupported_claims)} unsupported claims")
        
        low_confidence_citations = [c for c in citations if c.get('confidence', 1.0) < 0.5]
        if low_confidence_citations:
            recommendations.append(f"Improve citation matching for {len(low_confidence_citations)} citations")
        
        return recommendations
    
    def save_validation_result(self, graph_id: str, validation_result: Dict[str, Any]):
        """Save validation result to database with proper error handling"""
        
        # Input validation
        if not graph_id or not isinstance(graph_id, str):
            raise ValueError("Graph ID must be a non-empty string")
        
        if not validation_result or not isinstance(validation_result, dict):
            raise ValueError("Validation result must be a non-empty dictionary")
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                validation_id = f"{graph_id}_validation"
                cursor.execute('''
                    INSERT OR REPLACE INTO validation_results 
                    (id, graph_id, validation_data, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    validation_id,
                    graph_id,
                    json.dumps(validation_result, default=str),
                    datetime.now(timezone.utc).isoformat()
                ))
                
                conn.commit()
                self.logger.info(f"Saved validation result for graph {graph_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to save validation result for graph {graph_id}: {str(e)}", exc_info=True)
            raise
    
    def load_validation_result(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Load validation result from database with proper error handling"""
        
        # Input validation
        if not graph_id or not isinstance(graph_id, str):
            raise ValueError("Graph ID must be a non-empty string")
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT validation_data FROM validation_results WHERE id = ?
                ''', (f"{graph_id}_validation",))
                
                result = cursor.fetchone()
                
                if result:
                    try:
                        return json.loads(result[0])
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse validation data for graph {graph_id}: {str(e)}")
                        return None
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load validation result for graph {graph_id}: {str(e)}", exc_info=True)
            return None

# Tool functions for execution engine
def safe_hallucination_check(func):
    """Decorator for safe hallucination checking with error handling"""
    @wraps(func)
    def wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return func(args)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Hallucination check failed: {str(e)}", exc_info=True)
            return {
                'content': args.get('content_from', ''),
                'citations': [],
                'claims': [],
                'unsupported_claims': [],
                'hallucination_risk': 0.5,  # Medium risk when check fails
                'validation_passed': False,
                'recommendations': ['Hallucination check failed - manual review required'],
                'error': str(e)
            }
    return wrapper

@safe_hallucination_check
def hallucination_check(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate content for hallucinations and citation issues with comprehensive error handling"""
    
    # Input validation
    if not args or not isinstance(args, dict):
        raise ValueError("Arguments must be a non-empty dictionary")
    
    content = args.get('content_from', '')
    sources = args.get('citations_from', [])
    
    if not isinstance(content, str):
        raise ValueError("Content must be a string")
    
    if not isinstance(sources, list):
        raise ValueError("Sources must be a list")
    
    # Limit content size for processing
    if len(content) > 1024 * 1024:  # 1MB limit
        raise ValueError("Content too large for validation (max 1MB)")
    
    validator = CitationValidator()
    result = validator.detect_hallucinations(content, sources)
    
    # Save validation result
    graph_id = args.get('graph_id', 'unknown')
    try:
        validator.save_validation_result(graph_id, result)
    except Exception as e:
        # Log but don't fail the validation
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to save validation result: {str(e)}")
    
    return result

def extract_metadata(args: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata and citations from sources with input validation"""
    
    # Input validation
    if not args or not isinstance(args, dict):
        return {
            'processed_pdfs': [],
            'extracted_citations': [],
            'metadata': {},
            'error': 'Invalid arguments'
        }
    
    pdf_ids = args.get('pdf_ids_from', [])
    
    if not isinstance(pdf_ids, list):
        pdf_ids = []
    
    # Limit number of PDFs to process
    if len(pdf_ids) > 50:
        pdf_ids = pdf_ids[:50]
        logger = logging.getLogger(__name__)
        logger.warning("PDF list truncated to 50 items")
    
    # Placeholder - would implement actual PDF processing with error handling
    return {
        'processed_pdfs': pdf_ids,
        'extracted_citations': [],
        'metadata': {},
        'processing_status': 'placeholder_implementation'
    }

# Example usage
if __name__ == "__main__":
    validator = CitationValidator()
    
    # Test content
    test_content = """
    According to recent scholarship (Smith, 2023), the Genesis 1 creation narrative 
    demonstrates significant parallels with ancient Near Eastern cosmologies.
    Studies show that the Priestly author was influenced by Babylonian traditions.
    This can be seen at https://example.com/genesis-study.
    """
    
    test_sources = [
        {'title': 'Genesis 1 and Ancient Cosmology', 'url': 'https://example.com/genesis-study'},
        {'title': 'Smith, J. (2023). Creation Narratives in Context'}
    ]
    
    result = validator.detect_hallucinations(test_content, test_sources)
    print(json.dumps(result, indent=2))