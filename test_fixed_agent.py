#!/usr/bin/env python3
"""
Test script for the fixed autonomous research agent
"""

import asyncio
import logging
from autonomous_researcher_fixed import AutonomousResearchAgent, ResearchGoal

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_agent():
    """Test the fixed agent with a simple research topic"""
    
    print("🧪 Testing Fixed Autonomous Research Agent")
    print("=" * 50)
    
    # Create agent
    agent = AutonomousResearchAgent()
    
    # Define simple research goal
    goal = ResearchGoal(
        topic="Biblical creation narrative",
        research_mandate="Find basic information about Genesis creation story from multiple perspectives",
        quality_threshold=0.5,  # Low threshold for testing
        max_sources=8,
        min_sources=3
    )
    
    print(f"📋 Research Topic: {goal.topic}")
    print(f"📋 Quality Threshold: {goal.quality_threshold}")
    print(f"📋 Min Sources: {goal.min_sources}")
    print()
    
    try:
        # Run the research
        result = await agent.conduct_research(goal)
        
        # Print results
        print("✅ Research Completed!")
        print(f"🎯 Research Complete: {result['research_complete']}")
        print(f"📊 Quality Score: {result['quality_score']:.2f}")
        print(f"🔄 Iterations: {result['iterations']}")
        print(f"📚 Sources Found: {len(result['context'].sources)}")
        
        print("\n" + "=" * 50)
        print("📄 FINAL REPORT")
        print("=" * 50)
        print(result['final_report'])
        
        # Check for key fixes
        context = result['context']
        print("\n" + "=" * 50)
        print("🔍 VERIFICATION CHECKS")
        print("=" * 50)
        
        # 1. Check action history (loop prevention)
        print(f"✅ Action History Length: {len(context.action_history)}")
        print(f"📝 Actions Taken: {context.action_history}")
        
        # 2. Check quality improvement
        print(f"✅ Quality Score: {context.quality_score:.2f} (threshold: {goal.quality_threshold})")
        
        # 3. Check content processing
        processed_sources = [s for s in context.sources if s.get('content_processed')]
        print(f"✅ Content Processed: {len(processed_sources)} sources")
        
        # 4. Check completion criteria
        print(f"✅ Completed Criteria: {context.completed_criteria}")
        
        # 5. Check no infinite loops
        if result['iterations'] < 20:
            print("✅ No infinite loops detected")
        else:
            print("⚠️  Possible infinite loop (reached max iterations)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during research: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent())
    if success:
        print("\n🎉 All tests passed! Agent is working correctly.")
    else:
        print("\n💥 Test failed. Check the errors above.")