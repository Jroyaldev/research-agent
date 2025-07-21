"""
New Podcast Searcher
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import logging
import os
import podcastindex
import time

logger = logging.getLogger(__name__)

class NewPodcastSearcher:
    """
    Searches for podcast episodes from RSS feeds and fetches their transcripts.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.podcasts = {
            "BibleProject": "https://feeds.simplecast.com/3NVmUWZO",
            "BEMA": "https://feeds.fireside.fm/bema/rss",
            "OnScript": "https://feed.podbean.com/onscript/feed.xml",
            "Naked Bible": "https://nakedbiblepodcast.com/feed/podcast/",
            "Bible for Normal People": "https://feeds.megaphone.fm/ADL4119301527",
        }
        config = {
            "api_key": os.environ.get("PODCAST_INDEX_API_KEY"),
            "api_secret": os.environ.get("PODCAST_INDEX_API_SECRET")
        }
        self.podcast_index = podcastindex.init(config)
        self.feed_cache = {}
        self.cache_ttl = 3600  # 1 hour

    def search_all(self, query):
        """
        Searches all podcasts for a given query.
        """
        all_episodes = []
        for name, rss_url in self.podcasts.items():
            try:
                episodes = self.search(query, rss_url)
                for episode in episodes:
                    episode['podcast_name'] = name
                all_episodes.extend(episodes)
            except Exception as e:
                logger.error(f"Error searching {name}: {e}")

        # Also search podcast index
        try:
            index_episodes = self.search_podcast_index(query)
            all_episodes.extend(index_episodes)
        except Exception as e:
            logger.error(f"Error searching PodcastIndex: {e}")

        return all_episodes

    def search_podcast_index(self, query):
        """
        Searches the PodcastIndex for a given query.
        """
        results = self.podcast_index.search(query)
        episodes = []
        for feed in results['feeds']:
            feed_url = feed['url']
            feed_episodes = self.search(query, feed_url)
            for episode in feed_episodes:
                episode['podcast_name'] = feed['title']
            episodes.extend(feed_episodes)
        return episodes

    def search(self, query, rss_url):
        """
        Searches for podcast episodes from an RSS feed.
        """
        if rss_url in self.feed_cache and (time.time() - self.feed_cache[rss_url]['timestamp']) < self.cache_ttl:
            feed = self.feed_cache[rss_url]['feed']
        else:
            feed = feedparser.parse(rss_url)
            self.feed_cache[rss_url] = {'feed': feed, 'timestamp': time.time()}

        episodes = []
        for entry in feed.entries:
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            if query.lower() in title.lower() or query.lower() in summary.lower():
                transcript_url = None
                if hasattr(entry, 'podcast_transcript') and entry.podcast_transcript:
                    if isinstance(entry.podcast_transcript, list) and len(entry.podcast_transcript) > 0:
                        transcript_url = entry.podcast_transcript[0].get('url')
                    elif isinstance(entry.podcast_transcript, dict):
                        transcript_url = entry.podcast_transcript.get('url')

                episodes.append({
                    'title': title,
                    'url': entry.get('link'),
                    'summary': summary,
                    'transcript_url': transcript_url,
                })
        return episodes

    def fetch_transcript(self, episode_url, transcript_url=None):
        """
        Fetches the transcript of a podcast episode.
        """
        if transcript_url:
            try:
                response = self.session.get(transcript_url)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching transcript from URL: {e}")

        try:
            response = self.session.get(episode_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # This is a generic transcript extraction logic.
            # It might need to be customized for each podcast website.
            transcript_div = soup.find('div', class_='transcript')
            if transcript_div:
                return transcript_div.get_text(separator='\n').strip()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching episode content: {e}")
            return None
