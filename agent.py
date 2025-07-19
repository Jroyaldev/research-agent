"""
This module contains the Agent class, which is responsible for orchestrating the research process.
"""

from ai_research_agent_fallback import AIResearchAgentFallback

class Agent:
    """
    The Agent class is responsible for orchestrating the research process.
    """

    def __init__(self):
        self.research_agent = AIResearchAgentFallback()

    async def research(self, query):
        """
        Conducts research on a given query.
        """
        return await self.research_agent.conduct_research(query)
