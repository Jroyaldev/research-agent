import os
import requests
import json
import logging
from typing import Dict, Any, Optional
from functools import wraps
import time
from urllib.parse import quote_plus
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {str(e)}")
            raise last_exception
        return wrapper
    return decorator

def validate_search_query(query: str) -> str:
    """Validate and sanitize search query"""
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    
    # Remove potentially harmful characters
    query = re.sub(r'[<>"\\]', '', query.strip())
    
    # Limit length
    if len(query) > 500:
        query = query[:500]
        logger.warning("Query truncated to 500 characters")
    
    if len(query) < 2:
        raise ValueError("Query too short after sanitization")
    
    return query

@retry_on_failure(max_retries=3)
def web_search(query: str, max_results: int = 3) -> str:
    """Return search results as formatted string with comprehensive error handling"""
    
    # Input validation and sanitization
    try:
        query = validate_search_query(query)
        max_results = max(1, min(max_results, 10))  # Clamp between 1-10
    except ValueError as e:
        logger.error(f"Invalid search parameters: {str(e)}")
        return f"Search parameter error: {str(e)}"
    
    # Check for API key
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        logger.warning("BRAVE_API_KEY not found, search will fail")
        return "Search configuration error: API key not found. Please set BRAVE_API_KEY environment variable."
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
        "User-Agent": "Research-Agent/1.0"
    }
    params = {
        "q": query,
        "count": max_results,
        "text_decorations": False,
        "result_filter": "web",
        "safesearch": "moderate"
    }
    
    try:
        logger.info(f"Searching for: {query[:100]}...")
        
        # Make request with timeout
        response = requests.get(
            url, 
            headers=headers, 
            params=params, 
            timeout=15.0  # 15 second timeout
        )
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            return "Search error: Invalid response format from search API"
        
        web_results = data.get("web", {}).get("results", [])
        
        if not web_results:
            logger.info(f"No search results found for: {query}")
            return "No search results found for this query. Try rephrasing or using different keywords."
        
        # Process and format results
        results = []
        for i, item in enumerate(web_results[:max_results]):
            try:
                title = item.get('title', 'No title')[:200]  # Limit title length
                url_val = item.get('url', 'No URL')
                description = item.get('description', 'No description')[:300]  # Limit description
                
                # Basic URL validation
                if url_val and not url_val.startswith(('http://', 'https://')):
                    url_val = 'Invalid URL'
                
                results.append(
                    f"Title: {title}\n"
                    f"URL: {url_val}\n"
                    f"Description: {description}\n"
                )
            except Exception as e:
                logger.warning(f"Error processing search result {i}: {str(e)}")
                continue
        
        if not results:
            return "Search completed but no valid results could be processed."
        
        logger.info(f"Successfully found {len(results)} search results")
        return "\n".join(results)
        
    except requests.exceptions.Timeout:
        logger.error("Search request timed out")
        return "Search timeout: The search request took too long. Please try again."
    except requests.exceptions.ConnectionError:
        logger.error("Search connection error")
        return "Search connection error: Unable to connect to search service. Check your internet connection."
    except requests.exceptions.HTTPError as e:
        logger.error(f"Search HTTP error: {e.response.status_code} - {str(e)}")
        if e.response.status_code == 422:
            return f"Search parameter error: {e.response.text}"
        elif e.response.status_code == 429:
            return "Rate limit reached. Please wait a moment and try again."
        elif e.response.status_code == 401:
            return "Search authentication error: Invalid API key."
        elif e.response.status_code == 403:
            return "Search authorization error: API key lacks necessary permissions."
        else:
            return f"Search service error: HTTP {e.response.status_code}"
    except Exception as e:
        logger.error(f"Unexpected search error: {str(e)}", exc_info=True)
        return f"Unexpected search error: {str(e)}"

def validate_filename(filename: str) -> str:
    """Validate and sanitize filename"""
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename must be a non-empty string")
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename.strip())
    
    # Ensure it ends with .md
    if not filename.endswith('.md'):
        filename += '.md'
    
    # Limit length
    if len(filename) > 100:
        name_part = filename[:-3][:96]  # Leave room for .md
        filename = name_part + '.md'
    
    return filename

def save_note(filename: str, text: str) -> str:
    """Save text to a local markdown file with error handling"""
    try:
        # Input validation
        filename = validate_filename(filename)
        
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        # Limit text size (10MB max)
        if len(text.encode('utf-8')) > 10 * 1024 * 1024:
            raise ValueError("Text too large (max 10MB)")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        # Save file with proper encoding
        with open(filename, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")
        
        logger.info(f"Successfully saved note to {filename}")
        return f"Saved to {filename}"
        
    except ValueError as e:
        logger.error(f"Validation error saving note: {str(e)}")
        return f"Save error: {str(e)}"
    except OSError as e:
        logger.error(f"File system error saving note: {str(e)}")
        return f"File save error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error saving note: {str(e)}", exc_info=True)
        return f"Unexpected save error: {str(e)}"

def health_check() -> Dict[str, Any]:
    """Check the health of all tools and dependencies"""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "services": {}
    }
    
    # Check Brave API
    brave_key = os.getenv("BRAVE_API_KEY")
    if brave_key:
        try:
            # Quick test search
            test_result = web_search("test", max_results=1)
            if "error" not in test_result.lower():
                health_status["services"]["brave_search"] = "healthy"
            else:
                health_status["services"]["brave_search"] = "degraded"
                health_status["overall_status"] = "degraded"
        except Exception:
            health_status["services"]["brave_search"] = "unhealthy"
            health_status["overall_status"] = "degraded"
    else:
        health_status["services"]["brave_search"] = "unconfigured"
        health_status["overall_status"] = "degraded"
    
    # Check file system access
    try:
        test_file = "health_check_test.md"
        save_result = save_note(test_file, "test")
        if "error" not in save_result.lower():
            health_status["services"]["file_system"] = "healthy"
            # Clean up test file
            try:
                os.remove(test_file)
            except:
                pass
        else:
            health_status["services"]["file_system"] = "unhealthy"
            health_status["overall_status"] = "degraded"
    except Exception:
        health_status["services"]["file_system"] = "unhealthy"
        health_status["overall_status"] = "degraded"
    
    return health_status

@retry_on_failure(max_retries=3)
def fetch_content(url: str) -> str:
    """Fetch and extract main content from a web page"""
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return "Error: Invalid URL format"
            
        logger.info(f"Fetching content from: {url}")
        
        # Make request with timeout
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=15.0
        )
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Extract main content - try common content containers
        content_selectors = [
            'article', 'main', '.content', '#content', '.post-content',
            '.entry-content', '.article-body', '.story-body'
        ]
        
        content = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([elem.get_text(strip=True) for elem in elements])
                if len(content) > 200:  # Found substantial content
                    break
                    
        # Fallback to body if no specific container found
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(strip=True)
        
        # Clean up content
        content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
        content = content.strip()
        
        # Limit content size
        if len(content) > 5000:
            content = content[:5000] + "... [content truncated]"
            
        if len(content) < 50:
            return f"Error: Could not extract sufficient content from {url}"
            
        return content
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in fetch_content: {str(e)}")
        return f"Error processing content: {str(e)}"

@retry_on_failure(max_retries=3)
def validate_url(url: str) -> Dict[str, Any]:
    """Validate that a URL is accessible and returns valid content"""
    try:
        if not url or not url.startswith(('http://', 'https://')):
            return {
                "accessible": False,
                "status_code": None,
                "error": "Invalid URL format",
                "content_type": None
            }
            
        logger.info(f"Validating URL: {url}")
        
        response = requests.head(
            url,
            headers={"User-Agent": "Research-Agent/1.0"},
            timeout=10.0,
            allow_redirects=True
        )
        
        # If HEAD fails, try GET
        if response.status_code >= 400:
            response = requests.get(
                url,
                headers={"User-Agent": "Research-Agent/1.0"},
                timeout=10.0,
                stream=True
            )
            
        content_type = response.headers.get('content-type', '').lower()
        
        return {
            "accessible": response.status_code < 400,
            "status_code": response.status_code,
            "error": None,
            "content_type": content_type,
            "final_url": response.url
        }
        
    except Exception as e:
        return {
            "accessible": False,
            "status_code": None,
            "error": str(e),
            "content_type": None
        }

# JSON schema expected by Moonshot AI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date information with comprehensive error handling",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (2-500 characters)",
                        "minLength": 2,
                        "maxLength": 500
                    },
                    "max_results": {
                        "type": "integer", 
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save text to a local markdown note with validation",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename for the note (will be sanitized)",
                        "maxLength": 100
                    },
                    "text": {
                        "type": "string",
                        "description": "Text content to save",
                        "minLength": 1
                    }
                },
                "required": ["filename", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "health_check",
            "description": "Check the health status of all tools and services",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_content",
            "description": "Fetch and extract the main content from a web page for analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the web page to fetch content from",
                        "format": "uri"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_url",
            "description": "Validate that a URL is accessible and returns valid content",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to validate",
                        "format": "uri"
                    }
                },
                "required": ["url"]
            }
        }
    }
]
