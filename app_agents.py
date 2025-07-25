#!/usr/bin/env python3
"""
AI-Powered Research Application using Moonshot Kimi Model
"""

import time
import json
import os
import asyncio
import threading
from flask import Flask, request, jsonify, render_template
from enhanced_autonomous_researcher import EnhancedAutonomousResearchAgent, ResearchGoal
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

active_researches = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/research', methods=['POST'])
def start_research():
    data = request.get_json()
    query = data.get('query', '')

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    session_id = str(int(time.time() * 1000))
    
    def run_research_in_thread():
        """Run async research in a separate thread with its own event loop"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def research_worker():
                try:
                    active_researches[session_id]['status'] = 'running'
                    active_researches[session_id]['query'] = query
                    active_researches[session_id]['progress'] = 10
                    
                    # Create enhanced agent with validation
                    agent = EnhancedAutonomousResearchAgent()
                    goal = ResearchGoal(
                        topic=query,
                        research_mandate="Provide a comprehensive analysis that includes multiple scholarly perspectives, historical context, and contemporary applications.",
                        quality_threshold=0.7,
                        max_sources=12,
                        min_sources=3,
                        enable_validation=True
                    )
                    
                    # Store context for progress tracking
                    active_researches[session_id]['context'] = None
                    
                    # Conduct research using the enhanced agent
                    result = await agent.conduct_research(goal)
                    
                    # Store results
                    active_researches[session_id]['status'] = 'completed'
                    active_researches[session_id]['final_report'] = result.get('final_report', 'No report generated.')
                    active_researches[session_id]['sources'] = len(result.get('context', {}).sources or [])
                    active_researches[session_id]['quality_score'] = result.get('quality_score', 0.0)
                    active_researches[session_id]['context'] = result.get('context')
                    active_researches[session_id]['iterations'] = result.get('iterations', 0)
                    
                    logger.info(f"AI research completed for session {session_id}")
                    
                except Exception as e:
                    logger.error(f"Research failed for session {session_id}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    active_researches[session_id]['status'] = 'error'
                    active_researches[session_id]['error'] = str(e)
            
            # Run the research
            loop.run_until_complete(research_worker())
            loop.close()
            
        except Exception as e:
            logger.error(f"Thread error for session {session_id}: {str(e)}")
            active_researches[session_id]['status'] = 'error'
            active_researches[session_id]['error'] = str(e)

    # Initialize research status
    active_researches[session_id] = {
        'status': 'starting',
        'progress': 0,
        'current_step': 'Initializing AI research agent'
    }
    
    # Start research in background thread
    thread = threading.Thread(target=run_research_in_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})

@app.route('/api/research/<session_id>/status')
def get_research_status(session_id):
    research = active_researches.get(session_id)
    if not research:
        return jsonify({'error': 'Session not found'}), 404
    
    # Calculate real progress if agent context is available
    if research.get('status') == 'running' and 'context' in research and research['context']:
        context = research['context']
        
        # Calculate progress based on completion criteria
        total_criteria = len(context.goal.completion_criteria)
        completed_criteria = len(context.completed_criteria)
        progress = (completed_criteria / total_criteria) * 100 if total_criteria > 0 else 0
        
        # Ensure progress doesn't exceed 95% until completion
        progress = min(progress, 95)
        
        # Display the last action as the current step
        current_step = 'Initializing research...'
        if context.action_history:
            current_step = context.action_history[-1].replace('_', ' ').title()
        
        research['progress'] = progress
        research['current_step'] = current_step
        
        # Real agent activity
        research['agents'] = [
            {
                'agent': 'autonomous_researcher',
                'name': 'Autonomous Research Agent',
                'status': 'active',
                'message': current_step,
                'icon': '🧠',
                'color': '#4F46E5',
                'timestamp': time.time() * 1000
            }
        ]
    
    return jsonify(research)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test Moonshot API key
        moonshot_key = os.getenv("MOONSHOT_API_KEY")
        brave_key = os.getenv("BRAVE_API_KEY")
        
        return jsonify({
            'status': 'healthy',
            'moonshot_configured': bool(moonshot_key),
            'brave_configured': bool(brave_key),
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5020))  # Changed default port to 5020
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting AI Research Agent server on port {port}")
    logger.info(f"Moonshot API configured: {bool(os.getenv('MOONSHOT_API_KEY'))}")
    logger.info(f"Brave API configured: {bool(os.getenv('BRAVE_API_KEY'))}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
