"""
Web-based Biblical Podcast Search
Uses web search to find podcast episodes from specific biblical study podcasts
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from tools import web_search
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PodcastEpisode:
    """Represents a podcast episode found via web search"""
    title: str
    url: str
    description: str
    podcast_name: str
    relevance_score: float = 0.0
    biblical_references: List[str] = None

class BiblicalPodcastWebSearcher:
    """Searches for biblical podcast episodes using web search"""
    
    def __init__(self):
        # Define target podcasts with search strategies
        self.podcasts = {
            "Bible Project": {
                "search_terms": ["site:bibleproject.com", "bible project podcast"],
                "url_patterns": ["bibleproject.com"],
                "quality_boost": 2
            },
            "Bema": {
                "search_terms": ["site:bemadiscipleship.com", "bema podcast"],
                "url_patterns": ["bemadiscipleship.com", "bema"],
                "quality_boost": 1
            },
            "OnScript": {
                "search_terms": ["site:onscript.study", "onscript podcast"],
                "url_patterns": ["onscript.study"],
                "quality_boost": 2
            },
            "Naked Bible Podcast": {
                "search_terms": ["naked bible podcast", "site:nakedbiblepodcast.com"],
                "url_patterns": ["nakedbiblepodcast.com", "naked bible"],
                "quality_boost": 2
            },
            "Bible for Normal People": {
                "search_terms": ["bible for normal people", "site:peteenns.com"],
                "url_patterns": ["peteenns.com", "bible for normal people"],
                "quality_boost": 1
            }
        }
    
    def extract_biblical_references(self, query: str) -> Tuple[Optional[str], Optional[int], List[str]]:
        """Extract biblical book and chapter references from query"""
        
        # Common biblical books (simplified list)
        books = [
            'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
            'joshua', 'judges', 'ruth', 'samuel', 'kings', 'chronicles',
            'ezra', 'nehemiah', 'esther', 'job', 'psalms', 'proverbs',
            'ecclesiastes', 'song of songs', 'isaiah', 'jeremiah',
            'lamentations', 'ezekiel', 'daniel', 'hosea', 'joel', 'amos',
            'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk', 'zephaniah',
            'haggai', 'zechariah', 'malachi', 'matthew', 'mark', 'luke',
            'john', 'acts', 'romans', 'corinthians', 'galatians',
            'ephesians', 'philippians', 'colossians', 'thessalonians',
            'timothy', 'titus', 'philemon', 'hebrews', 'james', 'peter',
            'jude', 'revelation'
        ]
        
        # Abbreviations
        abbreviations = {
            'gen': 'genesis', 'ex': 'exodus', 'rom': 'romans', 'cor': 'corinthians',
            'gal': 'galatians', 'eph': 'ephesians', 'phil': 'philippians',
            'col': 'colossians', 'thess': 'thessalonians', 'tim': 'timothy',
            'heb': 'hebrews', 'jas': 'james', 'pet': 'peter', 'rev': 'revelation',
            'matt': 'matthew', 'mk': 'mark', 'lk': 'luke', 'jn': 'john'
        }
        
        query_lower = query.lower()
        found_references = []
        primary_book = None
        primary_chapter = None
        
        # Look for full book names
        for book in books:
            if book in query_lower:
                found_references.append(book)
                if not primary_book:
                    primary_book = book
                    
                    # Look for chapter number
                    patterns = [
                        rf'{re.escape(book)}\s+(\d+)',
                        rf'{re.escape(book)}\s+chapter\s+(\d+)',
                        rf'chapter\s+(\d+).*{re.escape(book)}',
                        rf'(\d+)\s*:\s*\d+.*{re.escape(book)}'  # verse reference
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, query_lower)
                        if match:
                            primary_chapter = int(match.group(1))
                            break
        
        # Check abbreviations
        for abbrev, full_name in abbreviations.items():
            if abbrev in query_lower and full_name not in found_references:
                found_references.append(full_name)
                if not primary_book:
                    primary_book = full_name
                    
                    # Look for chapter number with abbreviation
                    abbrev_pattern = rf'{re.escape(abbrev)}\s+(\d+)'
                    match = re.search(abbrev_pattern, query_lower)
                    if match:
                        primary_chapter = int(match.group(1))
        
        return primary_book, primary_chapter, found_references
    
    async def search_podcasts(self, query: str, max_results: int = 10) -> List[PodcastEpisode]:
        """Search for podcast episodes using web search"""
        
        logger.info(f"Searching biblical podcasts for: {query}")
        
        # Extract biblical references
        primary_book, primary_chapter, all_references = self.extract_biblical_references(query)
        
        logger.info(f"Detected biblical references: {all_references}")
        if primary_book:
            logger.info(f"Primary reference: {primary_book} {primary_chapter or ''}")
        
        all_episodes = []
        
        # Search each podcast
        for podcast_name, config in self.podcasts.items():
            try:
                logger.info(f"Searching {podcast_name}...")
                episodes = await self._search_single_podcast(
                    podcast_name, config, query, primary_book, primary_chapter
                )
                all_episodes.extend(episodes)
                
                # Add delay between searches
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error searching {podcast_name}: {e}")
                continue
        
        # Score and sort episodes
        scored_episodes = self._score_episodes(all_episodes, query, all_references)
        
        # Return top episodes
        return sorted(scored_episodes, key=lambda x: x.relevance_score, reverse=True)[:max_results]
    
    async def _search_single_podcast(self, podcast_name: str, config: Dict, query: str,
                                   primary_book: Optional[str], primary_chapter: Optional[int]) -> List[PodcastEpisode]:
        """Search for episodes from a single podcast"""
        
        episodes = []
        
        # Generate search queries for this podcast
        search_queries = self._generate_search_queries(config, query, primary_book, primary_chapter)
        
        for search_query in search_queries[:2]:  # Limit to 2 searches per podcast
            try:
                logger.info(f"Searching: {search_query}")
                
                # Perform web search
                search_results = web_search(search_query, max_results=5)
                
                if search_results:
                    # Parse search results
                    parsed_episodes = self._parse_search_results(
                        search_results, podcast_name, config
                    )
                    episodes.extend(parsed_episodes)
                
                # Add delay between searches
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Search failed for {podcast_name} with query '{search_query}': {e}")
                continue
        
        # Remove duplicates based on URL
        unique_episodes = []
        seen_urls = set()
        
        for episode in episodes:
            if episode.url not in seen_urls:
                unique_episodes.append(episode)
                seen_urls.add(episode.url)
        
        logger.info(f"Found {len(unique_episodes)} unique episodes for {podcast_name}")
        return unique_episodes[:3]  # Limit per podcast
    
    def _generate_search_queries(self, config: Dict, query: str, 
                               primary_book: Optional[str], primary_chapter: Optional[int]) -> List[str]:
        """Generate targeted search queries for a podcast"""
        
        search_queries = []
        base_terms = config["search_terms"]
        
        # If we have biblical references, create targeted searches
        if primary_book:
            book_chapter = f"{primary_book}"
            if primary_chapter:
                book_chapter += f" chapter {primary_chapter}"
            
            # Targeted biblical searches
            for base_term in base_terms:
                search_queries.append(f"{base_term} {book_chapter}")
                search_queries.append(f"{base_term} {primary_book}")
        
        # General query searches
        for base_term in base_terms:
            search_queries.append(f"{base_term} {query}")
        
        # Fallback searches
        if not search_queries:
            search_queries = [f"{term} podcast episode" for term in base_terms]
        
        return search_queries
    
    def _parse_search_results(self, search_results: str, podcast_name: str, config: Dict) -> List[PodcastEpisode]:
        """Parse web search results into podcast episodes"""
        
        episodes = []
        lines = search_results.split('\n')
        current_episode = {}
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Title: '):
                # Save previous episode if exists
                if current_episode and self._is_relevant_episode(current_episode, config):
                    episode = PodcastEpisode(
                        title=current_episode.get('title', 'Untitled'),
                        url=current_episode.get('url', ''),
                        description=current_episode.get('description', ''),
                        podcast_name=podcast_name,
                        relevance_score=1.0
                    )
                    episodes.append(episode)
                
                # Start new episode
                current_episode = {'title': line[7:]}
                
            elif line.startswith('URL: ') and current_episode:
                current_episode['url'] = line[5:]
                
            elif line.startswith('Description: ') and current_episode:
                current_episode['description'] = line[13:]
        
        # Don't forget the last episode
        if current_episode and self._is_relevant_episode(current_episode, config):
            episode = PodcastEpisode(
                title=current_episode.get('title', 'Untitled'),
                url=current_episode.get('url', ''),
                description=current_episode.get('description', ''),
                podcast_name=podcast_name,
                relevance_score=1.0
            )
            episodes.append(episode)
        
        return episodes
    
    def _is_relevant_episode(self, episode_data: Dict, config: Dict) -> bool:
        """Check if an episode is relevant to the target podcast"""
        
        url = episode_data.get('url', '').lower()
        title = episode_data.get('title', '').lower()
        description = episode_data.get('description', '').lower()
        
        # Check if URL matches podcast patterns
        url_patterns = config.get("url_patterns", [])
        for pattern in url_patterns:
            if pattern.lower() in url:
                return True
        
        # Check if content mentions podcast
        content = f"{title} {description}"
        for pattern in url_patterns:
            if pattern.lower() in content:
                return True
        
        # Look for podcast-specific keywords
        podcast_keywords = {
            "Bible Project": ["bible project", "bibleproject", "tim mackie"],
            "Bema": ["bema", "marty solomon"],
            "OnScript": ["onscript", "on script"],
            "Naked Bible Podcast": ["naked bible", "michael heiser"],
            "Bible for Normal People": ["pete enns", "normal people"]
        }
        
        # Get podcast name from config or infer
        for podcast, keywords in podcast_keywords.items():
            if any(keyword in content for keyword in keywords):
                return True
        
        return False
    
    def _score_episodes(self, episodes: List[PodcastEpisode], query: str, 
                       biblical_references: List[str]) -> List[PodcastEpisode]:
        """Score episodes based on relevance"""
        
        query_terms = query.lower().split()
        
        for episode in episodes:
            score = 1.0  # Base score
            
            title_lower = episode.title.lower()
            desc_lower = episode.description.lower()
            content = f"{title_lower} {desc_lower}"
            
            # Boost for biblical references
            for ref in biblical_references:
                if ref in title_lower:
                    score += 3
                elif ref in desc_lower:
                    score += 2
            
            # Boost for query terms
            for term in query_terms:
                if len(term) > 2:
                    if term in title_lower:
                        score += 2
                    elif term in desc_lower:
                        score += 1
            
            # Boost for academic podcasts
            if episode.podcast_name in ["OnScript", "Naked Bible Podcast"]:
                score += 1
            
            # Boost for episode indicators
            episode_indicators = ["episode", "ep ", "part", "series"]
            if any(indicator in title_lower for indicator in episode_indicators):
                score += 0.5
            
            episode.relevance_score = score
        
        return episodes

# Test function
async def test_podcast_search():
    """Test the podcast search functionality"""
    
    searcher = BiblicalPodcastWebSearcher()
    
    test_queries = [
        "Romans chapter 8",
        "Genesis creation",
        "Matthew 5 sermon on the mount"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing: {query}")
        print('='*50)
        
        episodes = await searcher.search_podcasts(query, max_results=5)
        
        if episodes:
            print(f"Found {len(episodes)} episodes:")
            for i, episode in enumerate(episodes, 1):
                print(f"\n{i}. {episode.podcast_name}: {episode.title}")
                print(f"   Score: {episode.relevance_score:.1f}")
                print(f"   URL: {episode.url}")
                print(f"   Description: {episode.description[:100]}...")
        else:
            print("No episodes found")

if __name__ == "__main__":
    asyncio.run(test_podcast_search())
