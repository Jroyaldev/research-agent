import unittest
from unittest.mock import patch, MagicMock
from podcast_search import NewPodcastSearcher

class TestNewPodcastSearcher(unittest.TestCase):

    @patch('podcast_search.PodcastIndex')
    def test_search_podcast_index(self, MockPodcastIndex):
        # Arrange
        mock_index_instance = MockPodcastIndex.return_value
        mock_index_instance.search.return_value = {
            'feeds': [
                {
                    'title': 'Test Podcast',
                    'url': 'http://test.com/feed.rss'
                }
            ]
        }
        searcher = NewPodcastSearcher()
        searcher.search = MagicMock(return_value=[])

        # Act
        searcher.search_podcast_index('test query')

        # Assert
        mock_index_instance.search.assert_called_with('test query')
        searcher.search.assert_called_with('test query', 'http://test.com/feed.rss')

    @patch('requests.Session.get')
    def test_fetch_transcript_with_transcript_url(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.text = "This is a transcript."
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        searcher = NewPodcastSearcher()

        # Act
        transcript = searcher.fetch_transcript('http://test.com/episode', 'http://test.com/transcript.txt')

        # Assert
        self.assertEqual(transcript, "This is a transcript.")
        mock_get.assert_called_with('http://test.com/transcript.txt')

    @patch('requests.Session.get')
    def test_fetch_transcript_without_transcript_url(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.text = "<html><body><div class='transcript'>This is a transcript from div.</div></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        searcher = NewPodcastSearcher()

        # Act
        transcript = searcher.fetch_transcript('http://test.com/episode')

        # Assert
        self.assertEqual(transcript, "This is a transcript from div.")
        mock_get.assert_called_with('http://test.com/episode')

if __name__ == '__main__':
    unittest.main()
