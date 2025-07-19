import asyncio
from autonomous_researcher import AutonomousResearchAgent, ResearchGoal

async def main():
    agent = AutonomousResearchAgent()
    goal = ResearchGoal(
        topic="MAtthew 2",
        research_mandate="Provide a comprehensive theological analysis that includes multiple scholarly perspectives, historical context, and contemporary applications. Must demonstrate academic rigor with properly cited sources.",
    )
    result = await agent.conduct_research(goal)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
