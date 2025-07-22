#!/usr/bin/env python3
"""
Test script for AI Research Agent
"""

import asyncio
import logging
from enhanced_autonomous_researcher import EnhancedAutonomousResearcher
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ai_research_agent():
    """Test the AI research agent with a simple query"""
    
    print("🧠 Testing AI Research Agent")
    print("=" * 50)
    
    try:
        # Create agent
        agent = EnhancedAutonomousResearcher()
        print("✅ AI Research Agent initialized successfully")
        
        # Test query
        test_query = "What are the latest developments in artificial intelligence?"
        print(f"🔍 Testing with query: {test_query}")
        
        # Conduct research
        result = await agent.conduct_research(test_query)
        
        print("\n📊 Research Results:")
        print(f"Query: {result['query']}")
        print(f"Sources Found: {result['sources_found']}")
        print(f"Quality Score: {result['quality_score']}")
        print(f"Iterations: {result['iterations']}")
        
        print("\n📝 Final Report Preview:")
        print("-" * 30)
        report_preview = result['final_report'][:500]
        print(f"{report_preview}...")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False

async def test_moonshot_connection():
    """Test Moonshot API connection"""
    
    print("\n🌙 Testing Moonshot API Connection")
    print("=" * 50)
    
    try:
        from moonshot_client import MoonshotClient
        
        client = MoonshotClient()
        print("✅ Moonshot client initialized")
        
        # Test simple completion
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello and confirm you're working."}
        ]
        
        response = await client.a_chat_completion(messages)
        
        if response and 'choices' in response:
            content = response['choices'][0]['message']['content']
            print(f"✅ Moonshot API response: {content[:100]}...")
            return True
        else:
            print("❌ Invalid response format")
            return False
            
    except Exception as e:
        print(f"❌ Moonshot connection failed: {str(e)}")
        return False

async def test_web_search():
    """Test web search functionality"""
    
    print("\n🔍 Testing Web Search")
    print("=" * 50)
    
    try:
        from tools import web_search
        
        result = web_search("artificial intelligence news", max_results=2)
        
        if result and "Title:" in result:
            print("✅ Web search working")
            print(f"Sample result: {result[:200]}...")
            return True
        else:
            print(f"❌ Web search failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Web search error: {str(e)}")
        return False

async def main():
    """Run all tests"""
    
    print("🚀 Starting AI Research Agent Tests")
    print("=" * 60)
    
    tests = [
        ("Moonshot API Connection", test_moonshot_connection()),
        ("Web Search", test_web_search()),
        ("AI Research Agent", test_ai_research_agent())
    ]
    
    results = []
    
    for test_name, test_coro in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The AI Research Agent is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())
