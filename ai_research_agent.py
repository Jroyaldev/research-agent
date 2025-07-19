"""
AI-Powered Research Agent using Moonshot Kimi Model
Real autonomous research with LLM-driven decision making
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import requests
from tools import web_search, save_note

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResearchContext:
    """Research state and memory"""
    query: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    insights: Dict[str, Any] = field(default_factory=dict)
    research_plan: Dict[str, Any] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    iteration_count: int = 0
    max_iterations: int = 10

class MoonshotClient:
    """Client for Moonshot AI API"""
    
    def __init__(self):
        self.api_key = os.getenv("MOONSHOT_API_KEY")
        if not self.api_key:
            raise ValueError("MOONSHOT_API_KEY not found in environment")
        
        self.base_url = "https://api.moonshot.ai/v1"
        self.model = "moonshot-v1-8k"  # Using Kimi model
        
    async def chat_completion(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Make chat completion request to Moonshot API"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Moonshot API error: {e}")
            raise

class AIResearchAgent:
    """AI-powered autonomous research agent"""
    
    def __init__(self):
        self.client = MoonshotClient()
        self.tools_schema = self._build_tools_schema()
        
    def _build_tools_schema(self) -> List[Dict]:
        """Build tools schema for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information using Brave Search API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find relevant information"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (1-10)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_sources",
                    "description": "Analyze and extract insights from collected sources",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sources": {
                                "type": "array",
                                "description": "List of sources to analyze"
                            },
                            "focus": {
                                "type": "string",
                                "description": "Specific aspect to focus analysis on"
                            }
                        },
                        "required": ["sources"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_research_note",
                    "description": "Save research findings to a note file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name for the research note file"
                            },
                            "content": {
                                "type": "string",
                                "description": "Research content to save"
                            }
                        },
                        "required": ["filename", "content"]
                    }
                }
            }
        ]
    
    async def conduct_research(self, query: str) -> Dict[str, Any]:
        """Main research orchestration using AI decision-making"""
        
        context = ResearchContext(query=query)
        
        logger.info(f"Starting AI research for: {query}")
        
        # Initial research planning
        await self._create_research_plan(context)
        
        # Execute research iterations
        while context.iteration_count < context.max_iterations:
            context.iteration_count += 1
            
            # AI decides next action
            next_action = await self._decide_next_action(context)
            
            if next_action.get("action") == "complete":
                break
                
            # Execute the action
            await self._execute_action(next_action, context)
            
            # Update quality assessment
            await self._assess_research_quality(context)
            
            # Check if research is complete
            if await self._is_research_complete(context):
                break
        
        # Generate final report
        final_report = await self._generate_final_report(context)
        
        return {
            "query": query,
            "final_report": final_report,
            "sources_found": len(context.sources),
            "quality_score": context.quality_score,
            "iterations": context.iteration_count,
            "research_plan": context.research_plan
        }
    
    async def _create_research_plan(self, context: ResearchContext):
        """AI creates initial research plan"""
        
        system_prompt = """You are an expert research coordinator. Analyze the research query and create a comprehensive research plan.

Your plan should include:
1. Research objectives and key questions
2. Information sources to explore
3. Research methodology
4. Quality criteria for sources
5. Expected deliverables

Be specific and actionable."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a research plan for: {context.query}"}
        ]
        
        try:
            response = await self.client.chat_completion(messages)
            plan_content = response["choices"][0]["message"]["content"]
            
            # Parse and structure the plan
            context.research_plan = {
                "raw_plan": plan_content,
                "created_at": datetime.now().isoformat(),
                "objectives": self._extract_objectives(plan_content),
                "methodology": self._extract_methodology(plan_content)
            }
            
            logger.info("Research plan created successfully")
            
        except Exception as e:
            logger.error(f"Error creating research plan: {e}")
            # Fallback plan
            context.research_plan = {
                "objectives": ["Gather comprehensive information", "Analyze sources", "Synthesize findings"],
                "methodology": "web_search_and_analysis"
            }
    
    async def _decide_next_action(self, context: ResearchContext) -> Dict[str, Any]:
        """AI decides what to do next based on current state"""
        
        system_prompt = """You are an autonomous research agent. Based on the current research state, decide what action to take next.

Available actions:
1. web_search - Search for more information
2. analyze_sources - Analyze collected sources for insights
3. save_research_note - Save current findings
4. complete - Finish research if sufficient quality achieved

Consider:
- Research completeness
- Source quality and diversity
- Information gaps
- Research objectives

Respond with a JSON object containing:
- action: the action to take
- reasoning: why this action is needed
- parameters: any parameters for the action"""

        # Build context summary
        context_summary = f"""
Research Query: {context.query}
Sources Collected: {len(context.sources)}
Completed Steps: {context.completed_steps}
Quality Score: {context.quality_score}
Iteration: {context.iteration_count}/{context.max_iterations}

Research Plan: {context.research_plan.get('objectives', [])}

Current Sources: {[s.get('title', 'Untitled')[:50] for s in context.sources[:3]]}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current research state:\n{context_summary}\n\nWhat should I do next?"}
        ]
        
        try:
            response = await self.client.chat_completion(messages, tools=self.tools_schema)
            
            # Check if AI wants to use a tool
            if response["choices"][0]["message"].get("tool_calls"):
                tool_call = response["choices"][0]["message"]["tool_calls"][0]
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                
                return {
                    "action": function_name,
                    "parameters": function_args,
                    "reasoning": "AI selected tool function"
                }
            else:
                # Parse text response for action
                content = response["choices"][0]["message"]["content"]
                return self._parse_action_from_text(content, context)
                
        except Exception as e:
            logger.error(f"Error deciding next action: {e}")
            return self._fallback_action(context)
    
    async def _execute_action(self, action: Dict[str, Any], context: ResearchContext):
        """Execute the decided action"""
        
        action_type = action.get("action")
        parameters = action.get("parameters", {})
        
        logger.info(f"Executing action: {action_type}")
        
        if action_type == "web_search":
            await self._execute_web_search(parameters, context)
        elif action_type == "analyze_sources":
            await self._execute_source_analysis(parameters, context)
        elif action_type == "save_research_note":
            await self._execute_save_note(parameters, context)
        else:
            logger.warning(f"Unknown action type: {action_type}")
    
    async def _execute_web_search(self, parameters: Dict[str, Any], context: ResearchContext):
        """Execute web search and add results to context"""
        
        query = parameters.get("query", context.query)
        max_results = parameters.get("max_results", 5)
        
        try:
            search_results = web_search(query, max_results)
            
            # Parse search results
            new_sources = self._parse_search_results(search_results)
            
            # Add to context with metadata
            for source in new_sources:
                source["search_query"] = query
                source["added_at"] = datetime.now().isoformat()
                source["source_type"] = "web_search"
            
            context.sources.extend(new_sources)
            context.completed_steps.append(f"web_search: {query}")
            
            logger.info(f"Added {len(new_sources)} sources from web search")
            
        except Exception as e:
            logger.error(f"Error executing web search: {e}")
    
    async def _execute_source_analysis(self, parameters: Dict[str, Any], context: ResearchContext):
        """Analyze sources using AI"""
        
        sources_to_analyze = parameters.get("sources", context.sources[-3:])  # Analyze recent sources
        focus = parameters.get("focus", "general analysis")
        
        system_prompt = f"""Analyze these research sources with focus on: {focus}

Extract:
1. Key insights and findings
2. Source credibility assessment
3. Relevance to research query
4. Notable quotes or data points
5. Gaps or limitations

Provide structured analysis."""

        sources_text = "\n\n".join([
            f"Title: {s.get('title', 'Untitled')}\nURL: {s.get('url', 'N/A')}\nDescription: {s.get('description', 'No description')}"
            for s in sources_to_analyze
        ])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Research Query: {context.query}\n\nSources to analyze:\n{sources_text}"}
        ]
        
        try:
            response = await self.client.chat_completion(messages)
            analysis = response["choices"][0]["message"]["content"]
            
            # Store analysis in context
            context.insights[f"analysis_{len(context.insights)}"] = {
                "content": analysis,
                "focus": focus,
                "sources_analyzed": len(sources_to_analyze),
                "created_at": datetime.now().isoformat()
            }
            
            context.completed_steps.append(f"source_analysis: {focus}")
            logger.info("Source analysis completed")
            
        except Exception as e:
            logger.error(f"Error analyzing sources: {e}")
    
    async def _execute_save_note(self, parameters: Dict[str, Any], context: ResearchContext):
        """Save research note"""
        
        filename = parameters.get("filename", f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        content = parameters.get("content", "")
        
        if not content:
            # Generate content from current context
            content = self._generate_note_content(context)
        
        try:
            result = save_note(filename, content)
            context.completed_steps.append(f"saved_note: {filename}")
            logger.info(f"Research note saved: {result}")
            
        except Exception as e:
            logger.error(f"Error saving note: {e}")
    
    async def _assess_research_quality(self, context: ResearchContext):
        """AI assesses current research quality"""
        
        system_prompt = """Assess the quality of this research based on:
1. Source diversity and credibility
2. Information completeness
3. Relevance to research query
4. Analysis depth

Provide a quality score from 0.0 to 1.0 and brief explanation."""

        research_summary = f"""
Query: {context.query}
Sources: {len(context.sources)}
Insights: {len(context.insights)}
Steps Completed: {context.completed_steps}

Recent Sources: {[s.get('title', 'Untitled')[:30] for s in context.sources[-3:]]}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": research_summary}
        ]
        
        try:
            response = await self.client.chat_completion(messages)
            quality_assessment = response["choices"][0]["message"]["content"]
            
            # Extract quality score (simple regex)
            import re
            score_match = re.search(r'(\d+\.?\d*)', quality_assessment)
            if score_match:
                context.quality_score = min(float(score_match.group(1)), 1.0)
            
            logger.info(f"Quality assessment: {context.quality_score}")
            
        except Exception as e:
            logger.error(f"Error assessing quality: {e}")
            # Fallback quality calculation
            context.quality_score = min(len(context.sources) * 0.1 + len(context.insights) * 0.2, 1.0)
    
    async def _is_research_complete(self, context: ResearchContext) -> bool:
        """Check if research meets completion criteria"""
        
        # Basic completion criteria
        has_sufficient_sources = len(context.sources) >= 3
        has_analysis = len(context.insights) >= 1
        meets_quality_threshold = context.quality_score >= 0.6
        
        return has_sufficient_sources and has_analysis and meets_quality_threshold
    
    async def _generate_final_report(self, context: ResearchContext) -> str:
        """AI generates comprehensive final report"""
        
        system_prompt = """Generate a comprehensive research report based on the collected information.

Structure:
1. Executive Summary
2. Key Findings
3. Source Analysis
4. Detailed Insights
5. Conclusions and Recommendations
6. Sources

Make it professional, well-structured, and actionable."""

        research_data = f"""
Research Query: {context.query}

Sources Collected ({len(context.sources)}):
{chr(10).join([f"- {s.get('title', 'Untitled')}: {s.get('url', 'N/A')}" for s in context.sources])}

Analysis Insights:
{chr(10).join([f"- {insight['content'][:200]}..." for insight in context.insights.values()])}

Research Plan: {context.research_plan.get('raw_plan', 'No plan available')}
Quality Score: {context.quality_score}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate final research report for:\n{research_data}"}
        ]
        
        try:
            response = await self.client.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            return self._generate_fallback_report(context)
    
    # Helper methods
    def _parse_search_results(self, search_results: str) -> List[Dict[str, Any]]:
        """Parse search results string into structured data"""
        sources = []
        lines = search_results.split('\n')
        current_source = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Title: '):
                if current_source:
                    sources.append(current_source)
                current_source = {'title': line[7:]}
            elif line.startswith('URL: ') and current_source:
                current_source['url'] = line[5:]
            elif line.startswith('Description: ') and current_source:
                current_source['description'] = line[13:]
        
        if current_source:
            sources.append(current_source)
        
        return sources
    
    def _extract_objectives(self, plan_content: str) -> List[str]:
        """Extract objectives from plan content"""
        # Simple extraction - could be improved with better parsing
        lines = plan_content.split('\n')
        objectives = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['objective', 'goal', 'aim']):
                objectives.append(line.strip())
        return objectives[:5]  # Limit to 5 objectives
    
    def _extract_methodology(self, plan_content: str) -> str:
        """Extract methodology from plan content"""
        if 'methodology' in plan_content.lower():
            return "structured_ai_research"
        return "general_research"
    
    def _parse_action_from_text(self, content: str, context: ResearchContext) -> Dict[str, Any]:
        """Parse action from AI text response"""
        content_lower = content.lower()
        
        if 'search' in content_lower and len(context.sources) < 5:
            return {
                "action": "web_search",
                "parameters": {"query": context.query, "max_results": 3},
                "reasoning": "Need more sources"
            }
        elif 'analyze' in content_lower and context.sources:
            return {
                "action": "analyze_sources",
                "parameters": {"sources": context.sources[-3:]},
                "reasoning": "Analyze recent sources"
            }
        elif 'complete' in content_lower or context.quality_score >= 0.7:
            return {
                "action": "complete",
                "reasoning": "Research appears complete"
            }
        else:
            return self._fallback_action(context)
    
    def _fallback_action(self, context: ResearchContext) -> Dict[str, Any]:
        """Fallback action when AI decision fails"""
        if len(context.sources) < 3:
            return {
                "action": "web_search",
                "parameters": {"query": context.query, "max_results": 3},
                "reasoning": "Fallback: need more sources"
            }
        elif not context.insights:
            return {
                "action": "analyze_sources",
                "parameters": {"sources": context.sources},
                "reasoning": "Fallback: need analysis"
            }
        else:
            return {
                "action": "complete",
                "reasoning": "Fallback: basic criteria met"
            }
    
    def _generate_note_content(self, context: ResearchContext) -> str:
        """Generate note content from context"""
        content = f"# Research: {context.query}\n\n"
        content += f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        content += f"## Sources ({len(context.sources)})\n"
        
        for i, source in enumerate(context.sources, 1):
            content += f"{i}. [{source.get('title', 'Untitled')}]({source.get('url', '#')})\n"
        
        content += "\n## Insights\n"
        for insight in context.insights.values():
            content += f"- {insight['content'][:100]}...\n"
        
        return content
    
    def _generate_fallback_report(self, context: ResearchContext) -> str:
        """Generate basic report when AI generation fails"""
        report = f"# Research Report: {context.query}\n\n"
        report += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += f"**Quality Score**: {context.quality_score}\n\n"
        
        report += f"## Sources Found ({len(context.sources)})\n"
        for i, source in enumerate(context.sources, 1):
            report += f"{i}. [{source.get('title', 'Untitled')}]({source.get('url', '#')})\n"
            if source.get('description'):
                report += f"   {source['description'][:150]}...\n"
        
        report += "\n## Research Process\n"
        for step in context.completed_steps:
            report += f"- {step}\n"
        
        return report

# Usage example
async def main():
    agent = AIResearchAgent()
    result = await agent.conduct_research("What are the latest developments in quantum computing?")
    print(result["final_report"])

if __name__ == "__main__":
    asyncio.run(main())
