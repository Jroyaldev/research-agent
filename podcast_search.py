"""
New Podcast Searcher
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import logging

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
            "Bible Project": "https://bibleproject.com/podcasts/the-bible-project-podcast/feed/",
            "Bema": "https://feeds.buzzsprout.com/1024493.rss",
            "OnScript": "https://feeds.buzzsprout.com/1208346.rss",
            "Naked Bible Podcast": "https://nakedbiblepodcast.com/feed/podcast/",
            "Bible for Normal People": "https://feeds.buzzsprout.com/418204.rss",
        }

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
        return all_episodes

    def search(self, query, rss_url):
        """
        Searches for podcast episodes from an RSS feed.
        """
        feed = feedparser.parse(rss_url)
        episodes = []
        for entry in feed.entries:
            if query.lower() in entry.title.lower() or query.lower() in entry.summary.lower():
                episodes.append({
                    'title': entry.title,
                    'url': entry.link,
                    'summary': entry.summary,
                })
        return episodes

    def fetch_transcript(self, episode_url):
        """
        Fetches the transcript of a podcast episode.
        """
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
