"""
AI-Powered Research Agent with Fallback (No Moonshot API required)
Uses rule-based logic when AI API is unavailable
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
from podcast_search import NewPodcastSearcher

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
    max_iterations: int = 8

class AIResearchAgentFallback:
    """AI-powered research agent with fallback logic"""
    
    def __init__(self):
        self.moonshot_available = self._check_moonshot_availability()
        if self.moonshot_available:
            try:
                from ai_research_agent import MoonshotClient
                self.client = MoonshotClient()
                logger.info("Moonshot AI client initialized successfully")
            except Exception as e:
                logger.warning(f"Moonshot client failed: {e}")
                self.moonshot_available = False
        
        if not self.moonshot_available:
            logger.info("Using fallback research logic (no AI API)")
        
        # Initialize podcast searcher
        self.podcast_searcher = NewPodcastSearcher()
    
    def _check_moonshot_availability(self) -> bool:
        """Check if Moonshot API is available"""
        api_key = os.getenv("MOONSHOT_API_KEY")
        return bool(api_key)
    
    async def conduct_research(self, query: str) -> Dict[str, Any]:
        """Main research orchestration with fallback logic"""
        
        context = ResearchContext(query=query)
        
        logger.info(f"Starting research for: {query}")
        
        # Create research plan
        await self._create_research_plan(context)
        
        # Execute research iterations
        while context.iteration_count < context.max_iterations:
            context.iteration_count += 1
            
            # Decide next action
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
            "research_plan": context.research_plan,
            "ai_powered": self.moonshot_available,
            "sources": context.sources,  # Include actual sources data
            "insights": context.insights,  # Include insights data
            "completed_steps": context.completed_steps,  # Include research steps
            "is_biblical_query": self._is_biblical_query(query),  # Flag for UI
            "podcast_episodes_found": len([s for s in context.sources if s.get('source_type') == 'podcast'])
        }
    
    async def _create_research_plan(self, context: ResearchContext):
        """Create research plan with AI or fallback"""
        
        if self.moonshot_available:
            try:
                # Try AI-powered planning
                system_prompt = "Create a research plan for the given query. Include objectives, methodology, and expected deliverables."
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create a research plan for: {context.query}"}
                ]
                
                response = await self.client.chat_completion(messages)
                plan_content = response["choices"][0]["message"]["content"]
                
                context.research_plan = {
                    "raw_plan": plan_content,
                    "created_at": datetime.now().isoformat(),
                    "objectives": self._extract_objectives(plan_content),
                    "methodology": "ai_powered_research"
                }
                
                logger.info("AI research plan created successfully")
                return
                
            except Exception as e:
                logger.warning(f"AI planning failed, using fallback: {e}")
        
        # Fallback planning
        context.research_plan = {
            "raw_plan": f"Comprehensive research plan for: {context.query}\n\n1. Gather diverse sources\n2. Analyze content quality\n3. Synthesize findings\n4. Generate comprehensive report",
            "created_at": datetime.now().isoformat(),
            "objectives": [
                "Collect relevant and credible sources",
                "Analyze information for key insights",
                "Assess source quality and reliability",
                "Synthesize findings into coherent report"
            ],
            "methodology": "systematic_web_research"
        }
        
        logger.info("Fallback research plan created")
    
    async def _decide_next_action(self, context: ResearchContext) -> Dict[str, Any]:
        """Decide next action with AI or rule-based logic"""
        
        # FORCE rule-based logic for biblical queries to ensure podcast search
        if self._is_biblical_query(context.query):
            logger.info("Using rule-based logic for biblical query to ensure podcast search")
            return self._rule_based_action(context)
        
        if self.moonshot_available:
            try:
                # Try AI decision making for non-biblical queries
                system_prompt = """Decide the next research action based on current state. 
                Available actions: web_search, analyze_sources, complete.
                Respond with JSON: {"action": "action_name", "reasoning": "why", "parameters": {...}}"""
                
                context_summary = f"""
                Query: {context.query}
                Sources: {len(context.sources)}
                Insights: {len(context.insights)}
                Iteration: {context.iteration_count}/{context.max_iterations}
                Quality: {context.quality_score}
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Current state:\n{context_summary}\n\nWhat should I do next?"}
                ]
                
                response = await self.client.chat_completion(messages)
                content = response["choices"][0]["message"]["content"]
                
                # Try to parse JSON response
                try:
                    return json.loads(content)
                except:
                    # Fall through to rule-based logic
                    pass
                    
            except Exception as e:
                logger.warning(f"AI decision making failed, using rules: {e}")
        
        # Rule-based decision making
        return self._rule_based_action(context)
    
    def _rule_based_action(self, context: ResearchContext) -> Dict[str, Any]:
        """Rule-based action selection"""
        
        # PRIORITY: Biblical podcast search - do this FIRST for biblical queries
        if (self._is_biblical_query(context.query) and 
            not any("podcast_search" in step for step in context.completed_steps)):
            return {
                "action": "podcast_search",
                "parameters": {"query": context.query, "max_results": 8},
                "reasoning": "Biblical query detected - prioritizing podcast search for enhanced biblical research"
            }
        
        # Need more sources
        if len(context.sources) < 5:
            search_queries = self._generate_search_queries(context)
            return {
                "action": "web_search",
                "parameters": {"query": search_queries[0], "max_results": 3},
                "reasoning": "Need more diverse sources"
            }
        
        # Need analysis
        if len(context.insights) < 2 and context.sources:
            return {
                "action": "analyze_sources",
                "parameters": {"sources": context.sources[-3:], "focus": "key_insights"},
                "reasoning": "Need to analyze collected sources"
            }
        
        # Quality check with higher threshold for biblical queries
        quality_threshold = 0.7 if self._is_biblical_query(context.query) else 0.6
        if context.quality_score < quality_threshold and context.iteration_count < 6:
            return {
                "action": "web_search",
                "parameters": {"query": f"{context.query} academic research", "max_results": 2},
                "reasoning": f"Need higher quality sources (target: {quality_threshold})"
            }
        
        # Complete research
        return {
            "action": "complete",
            "reasoning": "Research criteria met"
        }
    
    def _generate_search_queries(self, context: ResearchContext) -> List[str]:
        """Generate diverse search queries"""
        base_query = context.query
        
        queries = [
            base_query,
            f"{base_query} latest research",
            f"{base_query} academic study",
            f"{base_query} expert analysis",
            f"{base_query} recent developments"
        ]
        
        # Use different queries based on iteration
        return queries[context.iteration_count % len(queries):]
    
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
        elif action_type == "podcast_search":
            await self._execute_podcast_search(parameters, context)
    
    async def _execute_web_search(self, parameters: Dict[str, Any], context: ResearchContext):
        """Execute web search"""
        
        query = parameters.get("query", context.query)
        max_results = parameters.get("max_results", 3)
        
        try:
            search_results = web_search(query, max_results)
            new_sources = self._parse_search_results(search_results)
            
            # Add metadata
            for source in new_sources:
                source["search_query"] = query
                source["added_at"] = datetime.now().isoformat()
                source["source_type"] = "web_search"
                source["credibility_score"] = self._assess_source_credibility(source)
            
            context.sources.extend(new_sources)
            context.completed_steps.append(f"web_search: {query}")
            
            logger.info(f"Added {len(new_sources)} sources from web search")
            
        except Exception as e:
            logger.error(f"Error executing web search: {e}")
    
    async def _execute_source_analysis(self, parameters: Dict[str, Any], context: ResearchContext):
        """Analyze sources with AI or rule-based logic"""
        
        sources_to_analyze = parameters.get("sources", context.sources[-3:])
        focus = parameters.get("focus", "general analysis")
        
        if self.moonshot_available:
            try:
                # AI-powered analysis
                system_prompt = f"Analyze these sources focusing on: {focus}. Extract key insights, assess credibility, and identify important findings."
                
                sources_text = "\n\n".join([
                    f"Title: {s.get('title', 'Untitled')}\nURL: {s.get('url', 'N/A')}\nDescription: {s.get('description', 'No description')}"
                    for s in sources_to_analyze
                ])
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {context.query}\n\nSources:\n{sources_text}"}
                ]
                
                response = await self.client.chat_completion(messages)
                analysis = response["choices"][0]["message"]["content"]
                
                context.insights[f"ai_analysis_{len(context.insights)}"] = {
                    "content": analysis,
                    "focus": focus,
                    "sources_analyzed": len(sources_to_analyze),
                    "created_at": datetime.now().isoformat(),
                    "type": "ai_powered"
                }
                
                logger.info("AI source analysis completed")
                return
                
            except Exception as e:
                logger.warning(f"AI analysis failed, using fallback: {e}")
        
        # Fallback analysis
        analysis = self._rule_based_analysis(sources_to_analyze, context.query, focus)
        
        context.insights[f"rule_analysis_{len(context.insights)}"] = {
            "content": analysis,
            "focus": focus,
            "sources_analyzed": len(sources_to_analyze),
            "created_at": datetime.now().isoformat(),
            "type": "rule_based"
        }
        
        context.completed_steps.append(f"source_analysis: {focus}")
        logger.info("Rule-based source analysis completed")
    
    def _rule_based_analysis(self, sources: List[Dict], query: str, focus: str) -> str:
        """Rule-based source analysis"""
        
        analysis = f"## Source Analysis: {focus}\n\n"
        analysis += f"**Query**: {query}\n"
        analysis += f"**Sources Analyzed**: {len(sources)}\n\n"
        
        # Analyze each source
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Untitled')
            url = source.get('url', 'N/A')
            description = source.get('description', 'No description')
            credibility = source.get('credibility_score', 0.5)
            
            analysis += f"### Source {i}: {title}\n"
            analysis += f"**URL**: {url}\n"
            analysis += f"**Credibility Score**: {credibility:.2f}\n"
            analysis += f"**Summary**: {description[:200]}...\n"
            
            # Extract key themes
            themes = self._extract_themes(description, query)
            if themes:
                analysis += f"**Key Themes**: {', '.join(themes)}\n"
            
            analysis += "\n"
        
        # Overall assessment
        avg_credibility = sum(s.get('credibility_score', 0.5) for s in sources) / len(sources)
        analysis += f"## Overall Assessment\n"
        analysis += f"- **Average Credibility**: {avg_credibility:.2f}\n"
        analysis += f"- **Source Diversity**: {'High' if len(set(s.get('url', '').split('/')[2] for s in sources)) > 2 else 'Medium'}\n"
        analysis += f"- **Relevance**: {'High' if any(query.lower() in s.get('description', '').lower() for s in sources) else 'Medium'}\n"
        
        return analysis
    
    def _extract_themes(self, text: str, query: str) -> List[str]:
        """Extract key themes from text"""
        text_lower = text.lower()
        query_lower = query.lower()
        
        themes = []
        
        # Query-related themes
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 3 and word in text_lower:
                themes.append(word)
        
        # Common research themes
        research_themes = [
            'research', 'study', 'analysis', 'findings', 'results',
            'data', 'evidence', 'methodology', 'conclusion', 'impact'
        ]
        
        for theme in research_themes:
            if theme in text_lower:
                themes.append(theme)
        
        return list(set(themes))[:5]  # Return unique themes, max 5
    
    def _assess_source_credibility(self, source: Dict[str, Any]) -> float:
        """Assess source credibility based on URL and content"""
        
        url = source.get('url', '').lower()
        title = source.get('title', '').lower()
        description = source.get('description', '').lower()
        
        score = 0.5  # Base score
        
        # Domain credibility
        if any(domain in url for domain in ['.edu', '.gov', '.org']):
            score += 0.3
        elif any(domain in url for domain in ['wikipedia', 'britannica', 'scholar']):
            score += 0.2
        elif any(domain in url for domain in ['.com', '.net']):
            score += 0.1
        
        # Content indicators
        if any(word in description for word in ['research', 'study', 'academic', 'peer-reviewed']):
            score += 0.2
        
        if any(word in description for word in ['expert', 'professor', 'scientist', 'analysis']):
            score += 0.1
        
        # Negative indicators
        if any(word in url for word in ['blog', 'forum', 'social']):
            score -= 0.1
        
        return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
    
    async def _execute_save_note(self, parameters: Dict[str, Any], context: ResearchContext):
        """Save research note"""
        
        filename = parameters.get("filename", f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        content = parameters.get("content", "")
        
        if not content:
            content = self._generate_note_content(context)
        
        try:
            result = save_note(filename, content)
            context.completed_steps.append(f"saved_note: {filename}")
            logger.info(f"Research note saved: {result}")
        except Exception as e:
            logger.error(f"Error saving note: {e}")
    
    async def _assess_research_quality(self, context: ResearchContext):
        """Assess research quality"""
        
        if self.moonshot_available:
            try:
                # AI quality assessment
                system_prompt = "Assess research quality from 0.0 to 1.0 based on source diversity, credibility, and completeness. Respond with just the score and brief explanation."
                
                research_summary = f"""
                Query: {context.query}
                Sources: {len(context.sources)}
                Insights: {len(context.insights)}
                Steps: {context.completed_steps}
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": research_summary}
                ]
                
                response = await self.client.chat_completion(messages)
                quality_text = response["choices"][0]["message"]["content"]
                
                # Extract score
                import re
                score_match = re.search(r'(\d+\.?\d*)', quality_text)
                if score_match:
                    context.quality_score = min(float(score_match.group(1)), 1.0)
                    logger.info(f"AI quality assessment: {context.quality_score}")
                    return
                    
            except Exception as e:
                logger.warning(f"AI quality assessment failed: {e}")
        
        # Fallback quality calculation
        source_score = min(len(context.sources) * 0.15, 0.6)  # Up to 0.6 for sources
        insight_score = min(len(context.insights) * 0.2, 0.4)  # Up to 0.4 for insights
        
        # Credibility bonus
        if context.sources:
            avg_credibility = sum(s.get('credibility_score', 0.5) for s in context.sources) / len(context.sources)
            credibility_bonus = (avg_credibility - 0.5) * 0.2
        else:
            credibility_bonus = 0
        
        context.quality_score = min(source_score + insight_score + credibility_bonus, 1.0)
        logger.info(f"Rule-based quality assessment: {context.quality_score}")
    
    async def _is_research_complete(self, context: ResearchContext) -> bool:
        """Check if research is complete"""
        
        has_sources = len(context.sources) >= 3
        has_insights = len(context.insights) >= 1
        meets_quality = context.quality_score >= 0.5  # Lower threshold for fallback
        
        return has_sources and has_insights and meets_quality
    
    async def _generate_final_report(self, context: ResearchContext) -> str:
        """Generate final report with AI or template"""
        
        if self.moonshot_available:
            try:
                # AI report generation
                system_prompt = "Generate a comprehensive research report with executive summary, key findings, source analysis, and conclusions."
                
                research_data = f"""
                Query: {context.query}
                Sources ({len(context.sources)}): {[s.get('title', 'Untitled') for s in context.sources]}
                Insights: {[insight['content'][:100] + '...' for insight in context.insights.values()]}
                Quality Score: {context.quality_score}
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate report for:\n{research_data}"}
                ]
                
                response = await self.client.chat_completion(messages)
                return response["choices"][0]["message"]["content"]
                
            except Exception as e:
                logger.warning(f"AI report generation failed: {e}")
        
        # Fallback report generation
        return self._generate_fallback_report(context)
    
    def _generate_fallback_report(self, context: ResearchContext) -> str:
        """Generate structured fallback report"""
        
        report = f"# Research Report: {context.query}\n\n"
        report += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += f"**Research Method**: {'AI-Powered' if self.moonshot_available else 'Rule-Based'}\n"
        report += f"**Quality Score**: {context.quality_score:.2f}\n"
        report += f"**Sources Found**: {len(context.sources)}\n"
        report += f"**Analysis Depth**: {len(context.insights)} insights\n\n"
        
        # Executive Summary
        report += "## Executive Summary\n\n"
        report += f"This research investigated '{context.query}' through systematic web search and analysis. "
        report += f"A total of {len(context.sources)} sources were collected and analyzed, "
        report += f"resulting in {len(context.insights)} detailed insights. "
        report += f"The research achieved a quality score of {context.quality_score:.2f}.\n\n"
        
        # Key Findings
        report += "## Key Findings\n\n"
        if context.insights:
            for i, insight in enumerate(context.insights.values(), 1):
                report += f"### Finding {i}: {insight.get('focus', 'General Analysis')}\n"
                content = insight.get('content', '')
                # Extract first few sentences
                sentences = content.split('.')[:3]
                summary = '. '.join(sentences) + '.' if sentences else content[:200]
                report += f"{summary}\n\n"
        else:
            report += "Detailed analysis is available in the source collection below.\n\n"
        
        # Source Analysis
        report += "## Source Analysis\n\n"
        if context.sources:
            # Group by credibility
            high_cred = [s for s in context.sources if s.get('credibility_score', 0.5) >= 0.7]
            med_cred = [s for s in context.sources if 0.5 <= s.get('credibility_score', 0.5) < 0.7]
            low_cred = [s for s in context.sources if s.get('credibility_score', 0.5) < 0.5]
            
            report += f"**Source Quality Distribution**:\n"
            report += f"- High credibility sources: {len(high_cred)}\n"
            report += f"- Medium credibility sources: {len(med_cred)}\n"
            report += f"- Lower credibility sources: {len(low_cred)}\n\n"
            
            avg_cred = sum(s.get('credibility_score', 0.5) for s in context.sources) / len(context.sources)
            report += f"**Average Credibility Score**: {avg_cred:.2f}\n\n"
        
        # Separate sources by type
        web_sources = [s for s in context.sources if s.get('source_type') != 'podcast']
        podcast_sources = [s for s in context.sources if s.get('source_type') == 'podcast']
        
        # Web Sources
        if web_sources:
            report += "## Web Sources\n\n"
            for i, source in enumerate(web_sources, 1):
                title = source.get('title', 'Untitled')
                url = source.get('url', 'N/A')
                description = source.get('description', 'No description')
                credibility = source.get('credibility_score', 0.5)
                
                report += f"{i}. **{title}** (Credibility: {credibility:.2f})\n"
                report += f"   - URL: {url}\n"
                report += f"   - Summary: {description[:150]}...\n\n"
        
        # Podcast Episodes
        if podcast_sources:
            report += "## Recommended Podcast Episodes\n\n"
            report += "The following biblical study podcast episodes provide relevant insights and commentary:\n\n"
            
            # Group by podcast for better organization
            by_podcast = {}
            for source in podcast_sources:
                podcast_name = source.get('podcast_name', 'Unknown')
                if podcast_name not in by_podcast:
                    by_podcast[podcast_name] = []
                by_podcast[podcast_name].append(source)
            
            for podcast_name, episodes in by_podcast.items():
                report += f"### {podcast_name}\n\n"
                for episode in episodes:
                    title = episode.get('title', 'Untitled')
                    url = episode.get('url', 'N/A')
                    description = episode.get('description', 'No description')
                    relevance = episode.get('relevance_score', 0)
                    
                    report += f"- **[{title}]({url})** (Relevance: {relevance:.1f})\n"
                    report += f"  {description[:120]}...\n\n"
        
        # Research Process
        report += "## Research Process\n\n"
        report += f"**Iterations**: {context.iteration_count}\n"
        report += f"**Steps Completed**:\n"
        for step in context.completed_steps:
            report += f"- {step}\n"
        
        report += f"\n**Research Plan**: {context.research_plan.get('methodology', 'systematic_research')}\n\n"
        
        # Conclusions
        report += "## Conclusions\n\n"
        report += f"The research on '{context.query}' has been completed with "
        report += f"{'AI assistance' if self.moonshot_available else 'systematic methodology'}. "
        report += f"The findings are based on {len(context.sources)} sources with an average credibility of "
        
        if context.sources:
            avg_cred = sum(s.get('credibility_score', 0.5) for s in context.sources) / len(context.sources)
            report += f"{avg_cred:.2f}. "
        else:
            report += "N/A. "
        
        if context.quality_score >= 0.7:
            report += "The research meets high quality standards."
        elif context.quality_score >= 0.5:
            report += "The research meets acceptable quality standards."
        else:
            report += "Additional research may be beneficial for comprehensive coverage."
        
        report += "\n\n---\n"
        report += f"*Report generated by {'AI-Powered' if self.moonshot_available else 'Rule-Based'} Research Agent*"
        
        return report
    
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
        lines = plan_content.split('\n')
        objectives = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['objective', 'goal', 'aim']):
                objectives.append(line.strip())
        return objectives[:5]
    
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
    
    def _is_biblical_query(self, query: str) -> bool:
        """Check if query contains biblical references"""
        
        query_lower = query.lower()
        
        # Biblical books
        biblical_books = [
            'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
            'joshua', 'judges', 'ruth', 'samuel', 'kings', 'chronicles',
            'ezra', 'nehemiah', 'esther', 'job', 'psalms', 'proverbs',
            'ecclesiastes', 'song of songs', 'isaiah', 'jeremiah',
            'lamentations', 'ezekiel', 'daniel', 'hosea', 'joel', 'amos',
            'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk', 'zephaniah',
            'haggai', 'zechariah', 'malachi', 'matthew', 'mark', 'luke',
            'john', 'acts', 'romans', 'corinthians', 'galatians',
            'ephesians', 'philippians', 'colossians', 'thessalonians',
            'timothy', 'titus', 'philemon', 'hebrews', 'james', 'peter',
            'jude', 'revelation'
        ]
        
        # Biblical terms
        biblical_terms = [
            'bible', 'biblical', 'scripture', 'gospel', 'testament',
            'jesus', 'christ', 'god', 'lord', 'christian', 'christianity',
            'church', 'faith', 'theology', 'biblical studies', 'exegesis',
            'hermeneutics', 'apostle', 'disciple', 'prophet', 'messiah'
        ]
        
        # Check for biblical books
        for book in biblical_books:
            if book in query_lower:
                return True
        
        # Check for biblical terms
        for term in biblical_terms:
            if term in query_lower:
                return True
        
        # Check for chapter/verse patterns
        import re
        if re.search(r'\b\d+:\d+\b', query):  # verse reference pattern
            return True
        
        if re.search(r'\bchapter\s+\d+\b', query_lower):  # chapter reference
            return True
        
        return False
    
    async def _execute_podcast_search(self, parameters: Dict[str, Any], context: ResearchContext):
        """Execute podcast search for biblical content"""
        
        query = parameters.get("query", context.query)
        
        try:
            logger.info(f"Searching biblical podcasts for: {query}")
            
            # Search for podcast episodes
            episodes = self.podcast_searcher.search_all(query)
            
            # Convert episodes to sources format
            podcast_sources = []
            for episode in episodes:
                source = {
                    "title": episode['title'],
                    "url": episode['url'],
                    "description": episode['summary'],
                    "search_query": query,
                    "added_at": datetime.now().isoformat(),
                    "source_type": "podcast",
                    "podcast_name": episode['podcast_name'],
                    "relevance_score": 0, # Add a relevance score
                    "credibility_score": 0 # Add a credibility score
                }
                podcast_sources.append(source)
            
            context.sources.extend(podcast_sources)
            context.completed_steps.append(f"podcast_search: {query}")
            
            logger.info(f"Added {len(podcast_sources)} podcast episodes from search")
            
            # Add podcast insight
            if podcast_sources:
                podcast_analysis = self._analyze_podcast_episodes(podcast_sources, query)
                context.insights[f"podcast_analysis_{len(context.insights)}"] = {
                    "content": podcast_analysis,
                    "focus": "biblical_podcast_insights",
                    "sources_analyzed": len(podcast_sources),
                    "created_at": datetime.now().isoformat(),
                    "type": "podcast_analysis"
                }
            
        except Exception as e:
            logger.error(f"Error executing podcast search: {e}")
    
    def _assess_podcast_credibility(self, episode) -> float:
        """Assess podcast episode credibility"""
        
        # Base credibility by podcast
        podcast_credibility = {
            "OnScript": 0.9,  # Academic biblical scholarship
            "Naked Bible Podcast": 0.9,  # Scholarly approach
            "Bible Project": 0.8,  # Educational, well-researched
            "Bema": 0.7,  # Good content, less academic
            "Bible for Normal People": 0.7  # Accessible scholarship
        }
        
        base_score = podcast_credibility.get(episode.podcast_name, 0.6)
        
        # Boost for relevance
        relevance_boost = min(episode.relevance_score * 0.1, 0.2)
        
        # Boost for episode indicators
        title_lower = episode.title.lower()
        if any(term in title_lower for term in ['study', 'analysis', 'commentary', 'exegesis']):
            base_score += 0.1
        
        return min(base_score + relevance_boost, 1.0)
    
    def _analyze_podcast_episodes(self, episodes: List[Dict], query: str) -> str:
        """Analyze podcast episodes for insights"""
        
        analysis = f"## Biblical Podcast Analysis\n\n"
        analysis += f"**Query**: {query}\n"
        analysis += f"**Episodes Found**: {len(episodes)}\n\n"
        
        # Group by podcast
        by_podcast = {}
        for episode in episodes:
            podcast_name = episode.get('podcast_name', 'Unknown')
            if podcast_name not in by_podcast:
                by_podcast[podcast_name] = []
            by_podcast[podcast_name].append(episode)
        
        analysis += f"**Podcast Distribution**:\n"
        for podcast, eps in by_podcast.items():
            analysis += f"- {podcast}: {len(eps)} episodes\n"
        analysis += "\n"
        
        # Analyze top episodes
        sorted_episodes = sorted(episodes, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        analysis += "### Top Relevant Episodes\n\n"
        for i, episode in enumerate(sorted_episodes[:5], 1):
            title = episode.get('title', 'Untitled')
            podcast = episode.get('podcast_name', 'Unknown')
            relevance = episode.get('relevance_score', 0)
            credibility = episode.get('credibility_score', 0.5)
            
            analysis += f"**{i}. {title}** ({podcast})\n"
            analysis += f"- Relevance Score: {relevance:.1f}\n"
            analysis += f"- Credibility: {credibility:.2f}\n"
            analysis += f"- Description: {episode.get('description', 'No description')[:100]}...\n\n"
        
        # Overall assessment
        avg_relevance = sum(ep.get('relevance_score', 0) for ep in episodes) / len(episodes) if episodes else 0
        avg_credibility = sum(ep.get('credibility_score', 0.5) for ep in episodes) / len(episodes) if episodes else 0
        
        analysis += f"### Overall Assessment\n"
        analysis += f"- **Average Relevance**: {avg_relevance:.1f}\n"
        analysis += f"- **Average Credibility**: {avg_credibility:.2f}\n"
        analysis += f"- **Podcast Diversity**: {len(by_podcast)} different podcasts\n"
        analysis += f"- **Academic Quality**: {'High' if avg_credibility >= 0.8 else 'Medium' if avg_credibility >= 0.6 else 'Standard'}\n\n"
        
        analysis += "These podcast episodes provide biblical scholarship and commentary that complements the web research findings.\n"
        
        return analysis

# Usage example
async def main():
    agent = AIResearchAgentFallback()
    result = await agent.conduct_research("What are the latest developments in artificial intelligence?")
    print(result["final_report"])

if __name__ == "__main__":
    asyncio.run(main())
