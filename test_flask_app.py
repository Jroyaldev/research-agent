#!/usr/bin/env python3
"""
Test script for the Flask app
"""

import requests
import time
import json

def test_flask_app():
    """Test the Flask app research endpoint"""
    
    print("🧪 Testing Flask App Research Functionality")
    print("=" * 50)
    
    # Test data
    test_query = "Biblical creation narrative"
    base_url = "http://localhost:5022"
    
    try:
        # Start research
        print(f"📋 Starting research for: {test_query}")
        response = requests.post(
            f"{base_url}/api/research",
            json={"query": test_query},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"✅ Research started successfully. Session ID: {session_id}")
            
            # Poll for status
            max_polls = 30  # 30 seconds max
            for i in range(max_polls):
                time.sleep(1)
                
                status_response = requests.get(
                    f"{base_url}/api/research/{session_id}/status",
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status')
                    print(f"📊 Status ({i+1}s): {status}")
                    
                    if status == 'completed':
                        result = status_data.get('result', {})
                        print("✅ Research completed successfully!")
                        print(f"🎯 Quality Score: {result.get('quality_score', 'N/A')}")
                        print(f"🔄 Iterations: {result.get('iterations', 'N/A')}")
                        print(f"📚 Sources: {len(result.get('context', {}).get('sources', []))}")
                        print("\n📄 Report Preview:")
                        report = result.get('final_report', '')
                        print(report[:500] + "..." if len(report) > 500 else report)
                        return True
                    
                    elif status == 'error':
                        error = status_data.get('error', 'Unknown error')
                        print(f"❌ Research failed: {error}")
                        return False
                        
                else:
                    print(f"❌ Failed to get status: {status_response.status_code}")
                    return False
            
            print("⏱️ Research timed out")
            return False
            
        else:
            print(f"❌ Failed to start research: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error. Is the Flask app running?")
        print("💡 Start the app with: python app_agents.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_flask_app()
    if success:
        print("\n🎉 Flask app test passed!")
    else:
        print("\n💥 Flask app test failed.")