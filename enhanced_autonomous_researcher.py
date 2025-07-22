"""
Enhanced Autonomous Research Agent with Task Graph and Validation
Combines autonomous decision-making with structured task planning and validation
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import re
import requests
from bs4 import BeautifulSoup
from task_graph import TaskPlanner, ResearchGraph, Task
from validation_tools import CitationValidator, hallucination_check
from podcast_search import NewPodcastSearcher
from moonshot_client import MoonshotClient
from typing import Union

@dataclass
class ResearchGoal:
    """Enhanced research goal with validation requirements"""
    topic: str
    research_mandate: str
    quality_threshold: float = 0.6
    max_sources: int = 15
    min_sources: int = 5
    required_perspectives: List[str] = None
    completion_criteria: List[str] = None
    enable_validation: bool = True
    
    def __post_init__(self):
        if self.required_perspectives is None:
            self.required_perspectives = ["evangelical", "progressive", "orthodox", "academic"]
        if self.completion_criteria is None:
            self.completion_criteria = [
                "sufficient_sources_found",
                "multiple_perspectives_represented",
                "key_themes_identified",
                "quality_score_met",
                "citations_validated"
            ]

@dataclass
class ResearchContext:
    """Enhanced context with task graph integration and scratchpad"""
    goal: ResearchGoal
    sources: List[Dict[str, Any]] = None
    insights: Dict[str, Any] = None
    quality_score: float = 0.0
    current_focus: str = "initial_discovery"
    completed_criteria: List[str] = None
    failed_attempts: int = 0
    action_history: List[str] = None
    max_same_action_attempts: int = 3
    task_graph: Optional[ResearchGraph] = None
    validation_results: Dict[str, Any] = None
    scratchpad: List[Dict[str, str]] = None  # Added scratchpad for agent reasoning
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []
        if self.insights is None:
            self.insights = {}
        if self.completed_criteria is None:
            self.completed_criteria = []
        if self.action_history is None:
            self.action_history = []
        if self.scratchpad is None:  # Initialize scratchpad
            self.scratchpad = []
            
    def add_action(self, action: str):
        """Add an action to the action history"""
        self.action_history.append(action)
        
    def can_perform_action(self, action: str) -> bool:
        """Check if an action can be performed"""
        # Prevent too many of the same action in a row
        if len(self.action_history) >= self.max_same_action_attempts:
            recent_actions = self.action_history[-self.max_same_action_attempts:]
            if recent_actions.count(action) >= self.max_same_action_attempts:
                return False
        return True
        
    def add_to_scratchpad(self, thought: str, action: str, result: str = ""):
        """Add a reasoning step to the scratchpad"""
        self.scratchpad.append({
            "step": len(self.scratchpad) + 1,
            "thought": thought,
            "action": action,
            "result": result
        })

class EnhancedAutonomousResearchAgent:
    """Enhanced agent with task graph and validation capabilities"""
    
    def __init__(self):
        self.podcast_searcher = NewPodcastSearcher()
        # Moonshot LLM client for all language tasks
        self.llm = MoonshotClient()
        self.tools = {
            'web_search': self._web_search,
            'podcast_search': self._podcast_search,
            'extract_citations': self._extract_citations,
            'validate_source': self._validate_url,
            'synthesize_insights': self._synthesize_insights,
            'assess_quality': self._assess_quality,
            'identify_gaps': self._identify_gaps,
            'validate_content': self._validate_content
        }
        self.task_planner = TaskPlanner()
        self.validator = CitationValidator()
        
    async def conduct_research(self, goal: Union[ResearchGoal, str]) -> Dict[str, Any]:
        """Main research loop with task graph integration"""
        # If user passed a simple topic string, wrap it
        if isinstance(goal, str):
            goal = ResearchGoal(topic=goal, research_mandate="general inquiry")
        context = ResearchContext(goal=goal)
        
        # Create task graph for structured planning
        if goal.enable_validation:
            context.task_graph = self.task_planner.create_plan(goal.topic, "biblical_exegesis")
        
        logging.info(f"Starting enhanced research: {goal.topic}")
        logging.info(f"Task graph created with {len(context.task_graph.tasks)} tasks")
        
        max_iterations = 25
        iteration = 0
        
        while not await self._is_research_complete(context) and iteration < max_iterations:
            iteration += 1
            
            # Agent decides what to do next
            next_action = await self._decide_next_action(context)
            
            if next_action['action'] == 'complete':
                break
                
            # Execute action
            result = await self._execute_action(next_action, context)
            context = await self._update_context(context, result)
            
            # Validate content if enabled
            if goal.enable_validation and iteration % 5 == 0:
                await self._validate_research_content(context)
            
            context.add_action(next_action['action'])
            await asyncio.sleep(1)
        
        # Final validation
        if goal.enable_validation:
            await self._final_validation(context)
        
        final_report = await self._generate_enhanced_report(context)
        return {
            'research_complete': await self._is_research_complete(context),
            'final_report': final_report,
            'context': context,
            'iterations': iteration,
            'quality_score': context.quality_score,
        'query': context.goal.topic,
        'sources_found': len(context.sources),
            'validation_results': context.validation_results
        }
    
    async def _validate_research_content(self, context: ResearchContext):
        """Validate research content for hallucinations"""
        if not context.sources:
            return
            
        # Create content from sources and insights
        content = await self._create_validation_content(context)
        
        # Run validation
        validation_result = await self._validate_content({
            'content_from': content,
            'citations_from': context.sources,
            'graph_id': context.task_graph.graph_id if context.task_graph else 'research'
        })
        
        context.validation_results = validation_result
        
        # Update quality score based on validation
        if validation_result.get('validation_passed'):
            context.quality_score = min(context.quality_score + 0.1, 1.0)
    
    async def _create_validation_content(self, context: ResearchContext) -> str:
        """Create content for validation from research findings"""
        content = f"# Research on {context.goal.topic}\n\n"
        content += f"## Summary\n{context.goal.research_mandate}\n\n"
        
        # Add key insights
        if context.insights.get('key_themes'):
            content += "## Key Themes\n"
            for theme, count in context.insights['key_themes'].items():
                content += f"- {theme}: {count} sources\n"
        
        # Add source references
        content += "\n## Sources\n"
        for i, source in enumerate(context.sources, 1):
            title = source.get('title', 'Untitled')
            url = source.get('url', '')
            content += f"{i}. {title} - {url}\n"
        
        return content
    
    async def _validate_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content using validation tools"""
        return hallucination_check(args)
    
    async def _final_validation(self, context: ResearchContext):
        """Perform final validation of the complete research"""
        if not context.validation_results:
            await self._validate_research_content(context)
    
    async def _decide_next_action(self, context: ResearchContext) -> Dict[str, Any]:
        """Enhanced decision making with task graph awareness and scratchpad"""
        
        if context.failed_attempts >= 5:
            return {'action': 'complete', 'reason': 'max_attempts_reached'}
        
        # Add reasoning to scratchpad
        thought = "Deciding next action based on research progress"
        
        # Check task graph for next steps
        if context.task_graph:
            ready_tasks = self.task_planner.get_ready_tasks(context.task_graph)
            if ready_tasks:
                task = ready_tasks[0]
                context.add_to_scratchpad(
                    thought=thought,
                    action="execute_task",
                    result=f"Selected task: {task.tool} for {task.args.get('query', 'N/A')}"
                )
                return {
                    'action': 'execute_task',
                    'task': task
                }
        
        # Check for gaps instead of legacy fallback
        gap_result = await self._identify_gaps(context)
        context.add_to_scratchpad(
            thought=thought,
            action="identify_gaps",
            result=f"Found {len(gap_result['gaps'])} gaps"
        )
        if gap_result['suggestions']:
            # Add new tasks from suggestions
            last_task_id = context.task_graph.tasks[-1].id if context.task_graph.tasks else ""
            for idx, sugg in enumerate(gap_result['suggestions']):
                new_task = Task(
                    id=f"ADDED_{idx}_{datetime.now().isoformat()}",
                    tool="web_search",
                    args={"query": sugg['query']},
                    depends_on=[last_task_id] if last_task_id else []
                )
                context.task_graph.tasks.append(new_task)
            # After adding, get new ready tasks
            ready_tasks = self.task_planner.get_ready_tasks(context.task_graph)
            if ready_tasks:
                task = ready_tasks[0]
                return {
                    'action': 'execute_task',
                    'task': task
                }
        else:
            # No gaps, synthesize or complete
            if context.can_perform_action('synthesize_current_findings'):
                return {'action': 'synthesize_current_findings'}
            else:
                return {'action': 'complete', 'reason': 'no_gaps_found'}

        # If all else fails, complete
        return {'action': 'complete', 'reason': 'research_complete'}
    
    async def _legacy_decide_next_action(self, context: ResearchContext) -> Dict[str, Any]:
        """Original decision logic for backward compatibility"""
        
        if len(context.sources) < context.goal.min_sources:
            if context.can_perform_action('discover_sources'):
                return {
                    'action': 'discover_sources',
                    'strategy': 'broad_search',
                    'query': f"{context.goal.topic} theological commentary scholarly"
                }
        
        # Similar logic as original agent...
        return {'action': 'synthesize_current_findings'}
    
    async def _execute_action(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Execute actions including task graph tasks with scratchpad logging"""
        
        if action['action'] == 'execute_task':
            result = await self._execute_task(action['task'], context)
            context.add_to_scratchpad(
                thought=f"Executing task: {action['task'].tool}",
                action=action['action'],
                result=f"Task completed with status: {result['task'].status if 'task' in result else 'unknown'}"
            )
            return result
        
        # Handle legacy actions
        result = await self._execute_legacy_action(action, context)
        context.add_to_scratchpad(
            thought=f"Executing legacy action: {action['action']}",
            action=action['action'],
            result=f"Legacy action completed: {result}"
        )
        return result
    
    async def _execute_task(self, task: Task, context: ResearchContext) -> Dict[str, Any]:
        """Execute a task from the task graph"""
        
        task.status = "running"
        task.started_at = datetime.now().isoformat()
        
        try:
            # Execute based on task tool
            if task.tool == "web_search":
                results = await self._web_search(task.args.get("query", ""))
                task.result = results
                task.status = "completed"
                
            elif task.tool == "validate_source":
                # Use validation tools
                validation = await self._validate_sources_batch(context.sources)
                task.result = validation
                task.status = "completed"
                
            elif task.tool == "synthesize_research":
                insights = await self._synthesize_insights(context)
                task.result = insights
                task.status = "completed"
                
            else:
                task.status = "failed"
                task.error = f"Unknown task tool: {task.tool}"
                
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        
        task.completed_at = datetime.now().isoformat()
        
        return {
            'action': 'task_completed',
            'task': task,
            'result': task.result
        }
    
    async def _execute_legacy_action(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Execute legacy actions for backward compatibility"""
        
        if action['action'] == 'discover_sources':
            return await self._discover_sources(action, context)
        elif action['action'] == 'fetch_content':
            # Extract URL from action parameters
            url = action.get('url')
            if not url:
                return {'action': 'fetch_content', 'error': 'No URL provided'}
                
            # Fetch content
            content = await self._fetch_content(url)
            
            # Add to scratchpad
            context.add_to_scratchpad(
                thought=f"Fetching content from {url}",
                action="fetch_content",
                result=f"Retrieved {len(content)} characters" if not content.startswith('Error') else f"Failed to fetch: {content}"
            )
            
            return {
                'action': 'fetch_content',
                'url': url,
                'content': content,
                'success': not content.startswith('Error')
            }
        elif action['action'] == 'synthesize_current_findings':
            # Redirect legacy synthesis to the new Moonshot-powered insights
            return await self._synthesize_insights(context)
        
        return {'action': 'unknown_action'}
    
    async def _validate_sources_batch(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate multiple sources using validation tools"""
        validated_sources = []
        
        for source in sources:
            if source.get('url'):
                # Use the agent's validate_url method
                validation = await self._validate_url(source['url'])
                source['validation'] = validation
                validated_sources.append(source)
        
        return {
            'validated_sources': validated_sources,
            'valid_count': len([s for s in validated_sources if s.get('validation', {}).get('accessible', False)])
        }
    
    # Tool implementations (enhanced versions)
    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """Enhanced web search using Brave API only"""
        try:
            # Always use Brave search from tools.py
            from tools import web_search
            result = web_search(query, max_results=5)
            return self._parse_search_results(result)
        except Exception as e:
            logging.error(f"Error in web search: {e}")
            return []
            
    async def _fetch_content(self, url: str) -> str:
        """Fetch content from a URL using tools.py"""
        try:
            from tools import fetch_content
            return fetch_content(url)
        except Exception as e:
            logging.error(f"Error fetching content: {e}")
            return f"Error: {str(e)}"
            
    async def _validate_url(self, url: str) -> Dict[str, Any]:
        """Validate a URL using tools.py"""
        try:
            from tools import validate_url
            return validate_url(url)
        except Exception as e:
            logging.error(f"Error validating URL: {e}")
            return {"accessible": False, "error": str(e)}

    async def _podcast_search(self, query: str) -> List[Dict[str, Any]]:
        """Search podcasts using NewPodcastSearcher"""
        try:
            # Use asyncio.to_thread to run the synchronous search in a separate thread
            results = await asyncio.to_thread(self.podcast_searcher.search_all, query)
            
            # Format results to match expected structure
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'description': result.get('summary', '')[:500],
                    'transcript_url': result.get('transcript_url', ''),
                    'podcast_name': result.get('podcast_name', ''),
                    'source_type': 'podcast'
                })
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error in podcast search: {e}")
            return []

    async def _extract_citations(self, content: str) -> List[Dict[str, str]]:
        """Extract citations from content"""
        # Placeholder implementation - should be replaced with actual citation extraction logic
        logging.warning("Citation extraction not implemented yet")
        return []

    async def _synthesize_insights(self, context: ResearchContext) -> Dict[str, Any]:
        """Synthesize insights using Moonshot LLM for high-quality summaries and theme detection"""

        insights = {"key_themes": {}, "summaries": {}}
        themes = [
            "historical context",
            "theological implications",
            "scholarly consensus",
            "contemporary application",
        ]
        for theme in themes:
            insights["key_themes"][theme.replace(" ", "_")] = 0

        # Limit per-loop concurrency to avoid hitting rate limits
        async def process_source(src: Dict[str, Any]):
            url = src.get("url")
            if not url:
                return
            content = await self._fetch_content(url)
            if content.startswith("Error"):
                return
            # Summarize via Moonshot (truncate to 4000 chars for prompt safety)
            prompt_msgs = [
                {"role": "system", "content": "You are a scholarly research assistant."},
                {
                    "role": "user",
                    "content": (
                        "Summarize the following source in 3-4 concise, academic sentences, "
                        "highlighting key arguments and perspectives.\n\n" + content[:4000]
                    ),
                },
            ]
            summary = await self.llm.a_chat_completion_text(prompt_msgs, temperature=0.3)
            insights["summaries"][url] = summary
            lowercase = content.lower()
            for theme in themes:
                if theme in lowercase:
                    insights["key_themes"][theme.replace(" ", "_")] += 1

        await asyncio.gather(*(process_source(s) for s in context.sources[:10]))

        return {"action": "synthesize_insights", "insights": insights}

    async def _assess_quality(self, context: ResearchContext) -> Dict[str, Any]:
        """Assess the quality of research findings based on multiple criteria"""
        issues = []
        suggestions = []
        
        # Criteria weights
        weights = {
            'source_count': 0.2,
            'source_validation': 0.3,
            'perspective_coverage': 0.3,
            'insight_depth': 0.2
        }
        
        # 1. Source count score
        source_count_score = min(len(context.sources) / context.goal.min_sources, 1.0)
        if source_count_score < 1.0:
            issues.append(f"Insufficient sources: {len(context.sources)}/{context.goal.min_sources}")
        
        # 2. Source validation score
        validated_sources = [s for s in context.sources if s.get('validation', {}).get('accessible')]
        validation_score = len(validated_sources) / max(len(context.sources), 1)
        if validation_score < 0.8:
            issues.append(f"Low source validation rate: {validation_score:.2f}")
            suggestions.append("Improve source validation by re-checking or finding new sources.")

        # 3. Perspective coverage score
        required_perspectives = set(context.goal.required_perspectives)
        covered_perspectives = set(s.get('perspective', 'unknown') for s in context.sources)
        perspective_score = len(required_perspectives & covered_perspectives) / len(required_perspectives)
        if perspective_score < 1.0:
            issues.append(f"Missing perspectives: {', '.join(required_perspectives - covered_perspectives)}")

        # 4. Insight depth score (simple version)
        insight_depth_score = min(len(context.insights.get('summaries', {})) / max(len(context.sources), 1), 1.0)
        if insight_depth_score < 0.7:
            issues.append("Low insight depth: many sources are not summarized.")

        # Calculate final quality score
        quality_score = (
            source_count_score * weights['source_count'] +
            validation_score * weights['source_validation'] +
            perspective_score * weights['perspective_coverage'] +
            insight_depth_score * weights['insight_depth']
        )
        
        return {
            'action': 'assess_quality',
            'quality_score': min(quality_score, 1.0),
            'issues': issues,
            'suggestions': suggestions
        }

    async def _identify_gaps(self, context: ResearchContext) -> Dict[str, Any]:
        """Identify gaps in the research based on required perspectives and current insights"""
        gaps = []
        suggestions = []

        # Check for missing perspectives
        current_perspectives = set()
        for source in context.sources:
            if 'perspective' in source:  # Assuming sources may have perspective metadata
                current_perspectives.add(source['perspective'])

        missing_perspectives = set(context.goal.required_perspectives) - current_perspectives
        if missing_perspectives:
            gaps.append(f"Missing perspectives: {', '.join(missing_perspectives)}")
            for perspective in missing_perspectives:
                suggestions.append({
                    'action': 'discover_sources',
                    'strategy': 'targeted_search',
                    'query': f"{context.goal.topic} {perspective} perspective scholarly"
                })

        # Check for low coverage in key themes
        if context.insights.get('key_themes'):
            for theme, count in context.insights['key_themes'].items():
                if count < 2:  # Arbitrary threshold for sufficient coverage
                    gaps.append(f"Low coverage in {theme}: only {count} sources")
                    suggestions.append({
                        'action': 'discover_sources',
                        'strategy': 'theme_focused',
                        'query': f"{context.goal.topic} {theme} analysis"
                    })

        # Check source count
        if len(context.sources) < context.goal.min_sources:
            gaps.append(f"Insufficient sources: {len(context.sources)} found, need at least {context.goal.min_sources}")
            suggestions.append({
                'action': 'discover_sources',
                'strategy': 'broad_search',
                'query': f"{context.goal.topic} scholarly sources"
            })

        return {
            'action': 'identify_gaps',
            'gaps': gaps,
            'suggestions': suggestions
        }

    async def _generate_enhanced_report(self, context: ResearchContext) -> str:
        """Generate comprehensive report with narrative summaries and validation"""
        
        report = f"# Enhanced Research Report: {context.goal.topic}\n\n"
        report += f"**Research Mandate**: {context.goal.research_mandate}\n\n"
        report += f"**Quality Score**: {context.quality_score:.2f}\n\n"
        
        # Executive Summary – generated by Moonshot
        report += "## Executive Summary\n"
        # Use Moonshot to craft a scholarly narrative
        synthesis_prompt = [
            {"role": "system", "content": "You are an academic researcher writing a literature review."},
            {
                "role": "user",
                "content": (
                    f"Write a 600-word scholarly synthesis on the topic '{context.goal.topic}'.\n"
                    f"Key themes and counts: {context.insights.get('key_themes', {})}.\n"
                    "Use an academic tone, multiple viewpoints, and cite sources inline as (Author, Year)."
                ),
            },
        ]
        try:
            narrative = await self.llm.a_chat_completion_text(synthesis_prompt, temperature=0.4)
        except Exception as e:
            narrative = f"*LLM synthesis failed: {e}*"
        report += narrative + "\n"

        # Key Themes and Narratives
        if context.insights.get('key_themes'):
            report += "## Key Themes Analysis\n"
            for theme, count in context.insights['key_themes'].items():
                if count > 0:
                    theme_title = theme.replace('_', ' ').title()
                    report += f"### {theme_title}\n"
                    report += f"Found {count} sources discussing this theme.\n\n"
                    
                    # Add summaries for sources related to this theme
                    theme_summaries = []
                    for url, summary in context.insights.get('summaries', {}).items():
                        if theme.replace('_', ' ') in summary.lower():
                            source_title = next((s.get('title', 'Unknown') for s in context.sources if s.get('url') == url), "Unknown")
                            theme_summaries.append(f"- **{source_title}**: {summary}")
                    
                    if theme_summaries:
                        report += "\n".join(theme_summaries) + "\n\n"

        # Sources
        report += "\n## Sources\n"
        for i, source in enumerate(context.sources, 1):
            title = source.get('title', 'Untitled')
            url = source.get('url', '')
            validated = "✅" if source.get('validation', {}).get('accessible') else "❌"
            report += f"{i}. [{title}]({url}) {validated}\n"
        
        # Validation details
        if context.validation_results:
            report += "\n## Validation Results\n"
            report += f"- **Hallucination Risk**: {context.validation_results.get('hallucination_risk', 'N/A')}\n"
            report += f"- **Citations Validated**: {len([c for c in context.validation_results.get('citations', []) if c.get('validated')])}\n"
        
        # Agent Reasoning (optional, for debugging)
        if context.scratchpad:
            report += "\n<details>\n<summary>Agent Reasoning (Scratchpad)</summary>\n\n"
            for entry in context.scratchpad:
                report += f"**Step {entry['step']}**: {entry['thought']}\n- **Action**: {entry['action']}\n- **Result**: {entry['result']}\n\n"
            report += "</details>\n"
        
        return report
    
    # Legacy methods for backward compatibility
    async def _discover_sources(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Legacy source discovery"""
        search_results = await self._web_search(action.get('query', ''))
        new_sources = await self._filter_and_validate_sources(search_results)
        
        return {
            'action': 'discovered_sources',
            'new_sources': new_sources,
            'strategy': action.get('strategy', 'broad')
        }
    
    async def _filter_and_validate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and validate sources"""
        validated_sources = []
        for source in sources:
            if source.get('url'):
                validation = await self._validate_url(source['url'])
                if validation.get('accessible'):
                    source['validation'] = validation
                    validated_sources.append(source)
        return validated_sources
    

    
    def _parse_search_results(self, search_result: str) -> List[Dict[str, Any]]:
        """Parse search results"""
        sources = []
        lines = search_result.split('\n')
        current_source = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Title: '):
                if current_source:
                    sources.append(current_source)
                current_source = {'title': line[7:], 'url': '', 'description': ''}
            elif line.startswith('URL: ') and current_source:
                current_source['url'] = line[5:]
            elif line.startswith('Description: ') and current_source:
                current_source['description'] = line[13:]
        
        if current_source:
            sources.append(current_source)
        
        return sources
    
    async def _is_research_complete(self, context: ResearchContext) -> bool:
        """Check if research is complete"""
        criteria_status = {}
        
        # Check all completion criteria
        total_criteria = len(context.goal.completion_criteria)
        completed_criteria = len(context.completed_criteria)
        
        # Basic completion check
        basic_completion = (
            len(context.sources) >= context.goal.min_sources and
            context.quality_score >= context.goal.quality_threshold and
            len(context.completed_criteria) >= 3
        )
        
        return basic_completion

    async def _update_context(self, context: ResearchContext, result: Dict[str, Any]) -> ResearchContext:
        """Update research context with new results and log to scratchpad"""
        # Update sources if new sources were discovered
        if 'new_sources' in result:
            context.sources.extend(result['new_sources'])
            context.add_to_scratchpad(
                thought="Updating context with new sources",
                action="update_context",
                result=f"Added {len(result['new_sources'])} new sources"
            )
        
        # Update insights if new insights were synthesized
        if 'insights' in result:
            context.insights.update(result['insights'])
            context.add_to_scratchpad(
                thought="Updating context with new insights",
                action="update_context",
                result=f"Updated insights: {list(result['insights'].keys())}"
            )
        
        # Update quality score if provided
        if 'quality_score' in result:
            old_score = context.quality_score
            context.quality_score = result['quality_score']
            context.add_to_scratchpad(
                thought="Updating quality score",
                action="update_context",
                result=f"Quality score updated from {old_score:.2f} to {context.quality_score:.2f}"
            )
        
        # Update completed criteria if provided
        if 'completed_criteria' in result:
            context.completed_criteria.extend(result['completed_criteria'])
            context.add_to_scratchpad(
                thought="Updating completed criteria",
                action="update_context",
                result=f"Completed criteria: {result['completed_criteria']}"
            )
        
        # Update validation results if provided
        if 'validation_results' in result:
            context.validation_results = result['validation_results']
            context.add_to_scratchpad(
                thought="Updating validation results",
                action="update_context",
                result=f"Validation updated: {result['validation_results'].get('validation_passed', 'N/A')}"
            )
        
        return context

# Usage example
async def main():
    agent = EnhancedAutonomousResearchAgent()
    
    goal = ResearchGoal(
        topic="Genesis 1 creation narrative",
        research_mandate="Provide a comprehensive theological analysis with validation",
        quality_threshold=0.7,
        max_sources=12,
        enable_validation=True
    )
    
    result = await agent.conduct_research(goal)
    print(result['final_report'])

# Legacy alias for backward compatibility
EnhancedAutonomousResearcher = EnhancedAutonomousResearchAgent

if __name__ == "__main__":
    asyncio.run(main())
