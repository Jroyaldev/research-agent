"""
Biblical Podcast Search Agent
Searches specific biblical study podcasts for relevant episodes
"""

import os
import re
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urljoin, quote
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PodcastEpisode:
    """Represents a podcast episode with extracted content"""
    title: str
    url: str
    description: str
    podcast_name: str
    publication_date: str = ""
    duration: str = ""
    episode_number: str = ""
    transcript: str = ""
    show_notes: str = ""
    biblical_references: List[str] = None
    relevance_score: float = 0.0

class BiblicalPodcastSearcher:
    """Searches biblical study podcasts for relevant episodes"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Define target podcasts with their search strategies
        self.podcasts = {
            "Bible Project": {
                "website": "https://bibleproject.com",
                "search_method": "website_search",
                "rss_feed": "https://bibleproject.com/podcasts/the-bible-project-podcast/feed/",
                "search_patterns": ["bibleproject.com/podcast", "bibleproject.com/episodes"]
            },
            "Bema": {
                "website": "https://www.bemadiscipleship.com",
                "search_method": "rss_and_search",
                "rss_feed": "https://feeds.buzzsprout.com/1024493.rss",
                "search_patterns": ["bemadiscipleship.com", "bema podcast"]
            },
            "OnScript": {
                "website": "https://onscript.study",
                "search_method": "website_search",
                "rss_feed": "https://feeds.buzzsprout.com/1208346.rss",
                "search_patterns": ["onscript.study"]
            },
            "Naked Bible Podcast": {
                "website": "https://nakedbiblepodcast.com",
                "search_method": "rss_and_search",
                "rss_feed": "https://nakedbiblepodcast.com/feed/podcast/",
                "search_patterns": ["nakedbiblepodcast.com", "naked bible podcast"]
            },
            "Bible for Normal People": {
                "website": "https://peteenns.com",
                "search_method": "rss_and_search", 
                "rss_feed": "https://feeds.buzzsprout.com/418204.rss",
                "search_patterns": ["peteenns.com", "bible for normal people"]
            }
        }
    
    def extract_biblical_references(self, query: str) -> Tuple[Optional[str], Optional[int], List[str]]:
        """Extract biblical book and chapter references from query"""
        
        # Common biblical books
        books = [
            'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
            'joshua', 'judges', 'ruth', '1 samuel', '2 samuel', '1 kings', '2 kings',
            '1 chronicles', '2 chronicles', 'ezra', 'nehemiah', 'esther', 'job',
            'psalms', 'proverbs', 'ecclesiastes', 'song of songs', 'isaiah',
            'jeremiah', 'lamentations', 'ezekiel', 'daniel', 'hosea', 'joel',
            'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk', 'zephaniah',
            'haggai', 'zechariah', 'malachi', 'matthew', 'mark', 'luke', 'john',
            'acts', 'romans', '1 corinthians', '2 corinthians', 'galatians',
            'ephesians', 'philippians', 'colossians', '1 thessalonians',
            '2 thessalonians', '1 timothy', '2 timothy', 'titus', 'philemon',
            'hebrews', 'james', '1 peter', '2 peter', '1 john', '2 john',
            '3 john', 'jude', 'revelation'
        ]
        
        # Abbreviations mapping
        abbreviations = {
            'gen': 'genesis', 'ex': 'exodus', 'lev': 'leviticus', 'num': 'numbers',
            'deut': 'deuteronomy', 'josh': 'joshua', 'judg': 'judges',
            '1 sam': '1 samuel', '2 sam': '2 samuel', '1 kgs': '1 kings',
            '2 kgs': '2 kings', '1 chr': '1 chronicles', '2 chr': '2 chronicles',
            'ps': 'psalms', 'prov': 'proverbs', 'eccl': 'ecclesiastes',
            'song': 'song of songs', 'isa': 'isaiah', 'jer': 'jeremiah',
            'lam': 'lamentations', 'ezek': 'ezekiel', 'dan': 'daniel',
            'matt': 'matthew', 'mk': 'mark', 'lk': 'luke', 'jn': 'john',
            'rom': 'romans', '1 cor': '1 corinthians', '2 cor': '2 corinthians',
            'gal': 'galatians', 'eph': 'ephesians', 'phil': 'philippians',
            'col': 'colossians', '1 thess': '1 thessalonians', '2 thess': '2 thessalonians',
            '1 tim': '1 timothy', '2 tim': '2 timothy', 'tit': 'titus',
            'philem': 'philemon', 'heb': 'hebrews', 'jas': 'james',
            '1 pet': '1 peter', '2 pet': '2 peter', '1 jn': '1 john',
            '2 jn': '2 john', '3 jn': '3 john', 'rev': 'revelation'
        }
        
        query_lower = query.lower()
        found_references = []
        primary_book = None
        primary_chapter = None
        
        # Look for book and chapter patterns
        for book in books:
            if book in query_lower:
                found_references.append(book)
                if not primary_book:
                    primary_book = book
                    
                    # Look for chapter number after book name
                    book_pattern = rf'{re.escape(book)}\s+(\d+)'
                    match = re.search(book_pattern, query_lower)
                    if match:
                        primary_chapter = int(match.group(1))
        
        # Check abbreviations
        for abbrev, full_name in abbreviations.items():
            if abbrev in query_lower and full_name not in found_references:
                found_references.append(full_name)
                if not primary_book:
                    primary_book = full_name
                    
                    # Look for chapter number
                    abbrev_pattern = rf'{re.escape(abbrev)}\s+(\d+)'
                    match = re.search(abbrev_pattern, query_lower)
                    if match:
                        primary_chapter = int(match.group(1))
        
        return primary_book, primary_chapter, found_references
    
    async def search_podcasts(self, query: str, max_episodes_per_podcast: int = 3) -> List[PodcastEpisode]:
        """Search all target podcasts for relevant episodes"""
        
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
                    podcast_name, config, query, primary_book, primary_chapter, max_episodes_per_podcast
                )
                all_episodes.extend(episodes)
                
                # Add delay between requests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error searching {podcast_name}: {e}")
                continue
        
        # Score and sort episodes by relevance
        scored_episodes = self._score_episodes(all_episodes, query, all_references)
        
        # Return top episodes
        return sorted(scored_episodes, key=lambda x: x.relevance_score, reverse=True)[:15]
    
    async def _search_single_podcast(self, podcast_name: str, config: Dict, query: str, 
                                   primary_book: Optional[str], primary_chapter: Optional[int],
                                   max_episodes: int) -> List[PodcastEpisode]:
        """Search a single podcast for relevant episodes"""
        
        episodes = []
        
        # Try RSS feed first (most reliable)
        if config.get("rss_feed"):
            try:
                rss_episodes = await self._search_rss_feed(
                    podcast_name, config["rss_feed"], query, primary_book, primary_chapter
                )
                episodes.extend(rss_episodes[:max_episodes])
            except Exception as e:
                logger.warning(f"RSS search failed for {podcast_name}: {e}")
        
        # If we need more episodes, try website search
        if len(episodes) < max_episodes and config.get("search_method") == "website_search":
            try:
                website_episodes = await self._search_website(
                    podcast_name, config["website"], query, primary_book, primary_chapter
                )
                episodes.extend(website_episodes[:max_episodes - len(episodes)])
            except Exception as e:
                logger.warning(f"Website search failed for {podcast_name}: {e}")
        
        return episodes[:max_episodes]
    
    async def _search_rss_feed(self, podcast_name: str, rss_url: str, query: str,
                             primary_book: Optional[str], primary_chapter: Optional[int]) -> List[PodcastEpisode]:
        """Search podcast RSS feed for relevant episodes"""
        
        try:
            logger.info(f"Parsing RSS feed for {podcast_name}: {rss_url}")
            
            # Parse RSS feed
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                logger.warning(f"No entries found in RSS feed for {podcast_name}")
                return []
            
            episodes = []
            query_terms = query.lower().split()
            
            for entry in feed.entries[:50]:  # Check recent 50 episodes
                title = entry.get('title', '').lower()
                description = entry.get('description', '').lower()
                summary = entry.get('summary', '').lower()
                
                # Combine all text for searching
                full_text = f"{title} {description} {summary}"
                
                # Check relevance
                relevance = 0
                
                # Check for biblical book
                if primary_book and primary_book in full_text:
                    relevance += 3
                    
                    # Check for chapter
                    if primary_chapter:
                        chapter_patterns = [
                            f"{primary_book} {primary_chapter}",
                            f"chapter {primary_chapter}",
                            f"ch {primary_chapter}",
                            f"{primary_chapter}:"
                        ]
                        for pattern in chapter_patterns:
                            if pattern in full_text:
                                relevance += 2
                                break
                
                # Check for query terms
                for term in query_terms:
                    if len(term) > 2 and term in full_text:
                        relevance += 1
                
                # Only include if somewhat relevant
                if relevance >= 2:
                    episode = PodcastEpisode(
                        title=entry.get('title', 'Untitled'),
                        url=entry.get('link', ''),
                        description=entry.get('description', ''),
                        podcast_name=podcast_name,
                        publication_date=entry.get('published', ''),
                        duration=entry.get('itunes_duration', ''),
                        relevance_score=relevance
                    )
                    episodes.append(episode)
            
            logger.info(f"Found {len(episodes)} relevant episodes in {podcast_name} RSS")
            return episodes
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed for {podcast_name}: {e}")
            return []
    
    async def _search_website(self, podcast_name: str, website_url: str, query: str,
                            primary_book: Optional[str], primary_chapter: Optional[int]) -> List[PodcastEpisode]:
        """Search podcast website for episodes"""
        
        try:
            # This is a simplified website search - in practice, each site would need custom logic
            logger.info(f"Searching website for {podcast_name}: {website_url}")
            
            # For now, return empty list - website scraping would be implemented per site
            # Each podcast website has different structure and would need custom parsing
            return []
            
        except Exception as e:
            logger.error(f"Error searching website for {podcast_name}: {e}")
            return []
    
    def _score_episodes(self, episodes: List[PodcastEpisode], query: str, 
                       biblical_references: List[str]) -> List[PodcastEpisode]:
        """Score episodes based on relevance to query and biblical references"""
        
        query_terms = query.lower().split()
        
        for episode in episodes:
            score = episode.relevance_score
            
            title_lower = episode.title.lower()
            desc_lower = episode.description.lower()
            
            # Boost score for biblical references in title
            for ref in biblical_references:
                if ref in title_lower:
                    score += 2
                elif ref in desc_lower:
                    score += 1
            
            # Boost score for query terms
            for term in query_terms:
                if len(term) > 2:
                    if term in title_lower:
                        score += 1
                    elif term in desc_lower:
                        score += 0.5
            
            # Boost score for certain podcasts (academic quality)
            if episode.podcast_name in ["OnScript", "Naked Bible Podcast"]:
                score += 1
            
            episode.relevance_score = score
        
        return episodes

# Usage example
async def main():
    searcher = BiblicalPodcastSearcher()
    episodes = await searcher.search_podcasts("Romans chapter 8 suffering")
    
    print(f"Found {len(episodes)} relevant episodes:")
    for episode in episodes[:5]:
        print(f"\n{episode.podcast_name}: {episode.title}")
        print(f"Score: {episode.relevance_score}")
        print(f"URL: {episode.url}")
        print(f"Description: {episode.description[:150]}...")

if __name__ == "__main__":
    asyncio.run(main())
