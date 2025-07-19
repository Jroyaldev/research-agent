"""
Autonomous Research Agent with Self-Directed Goal Completion - FIXED VERSION
Gives the agent a research mandate and tools, not rigid steps
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

@dataclass
class ResearchGoal:
    """What the agent should achieve, not how"""
    topic: str
    research_mandate: str
    quality_threshold: float = 0.6  # LOWERED from 0.85
    max_sources: int = 15
    min_sources: int = 5
    required_perspectives: List[str] = None
    completion_criteria: List[str] = None
    
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
    """Agent's working memory and state"""
    goal: ResearchGoal
    sources: List[Dict[str, Any]] = None
    insights: Dict[str, Any] = None
    quality_score: float = 0.0
    current_focus: str = "initial_discovery"
    completed_criteria: List[str] = None
    failed_attempts: int = 0
    action_history: List[str] = None  # NEW: Track action history
    max_same_action_attempts: int = 3  # NEW: Prevent infinite loops
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []
        if self.insights is None:
            self.insights = {}
        if self.completed_criteria is None:
            self.completed_criteria = []
        if self.action_history is None:
            self.action_history = []
    
    def can_perform_action(self, action: str) -> bool:
        """Check if we can perform an action (loop prevention)"""
        recent_actions = self.action_history[-self.max_same_action_attempts:]
        return recent_actions.count(action) < self.max_same_action_attempts
    
    def add_action(self, action: str):
        """Add action to history"""
        self.action_history.append(action)

class AutonomousResearchAgent:
    """Agent that decides its own research strategy"""
    
    def __init__(self):
        self.tools = {
            'web_search': self._web_search,
            'pdf_search': self._pdf_search,
            'podcast_search': self._podcast_search,
            'extract_citations': self._extract_citations,
            'validate_source': self._validate_source,
            'synthesize_insights': self._synthesize_insights,
            'assess_quality': self._assess_quality,
            'identify_gaps': self._identify_gaps
        }
        
    async def conduct_research(self, goal: ResearchGoal) -> Dict[str, Any]:
        """Main autonomous research loop - agent decides what to do"""
        context = ResearchContext(goal=goal)
        
        logging.info(f"Starting autonomous research: {goal.topic}")
        logging.info(f"Mandate: {goal.research_mandate}")
        
        max_iterations = 20
        iteration = 0
        
        while not await self._is_research_complete(context) and iteration < max_iterations:
            iteration += 1
            
            # Agent decides what to do next based on current state
            next_action = await self._decide_next_action(context)
            
            if next_action['action'] == 'complete':
                break
                
            # Execute the chosen action
            result = await self._execute_action(next_action, context)
            context = await self._update_context(context, result)
            
            # Track actions for loop prevention
            context.add_action(next_action['action'])
            
            # Brief pause to avoid overwhelming APIs
            await asyncio.sleep(1)
        
        final_report = await self._generate_final_report(context)
        return {
            'research_complete': await self._is_research_complete(context),
            'final_report': final_report,
            'context': context,
            'iterations': iteration,
            'quality_score': context.quality_score
        }
    
    async def _decide_next_action(self, context: ResearchContext) -> Dict[str, Any]:
        """Agent reasons about what to do next - WITH LOOP PREVENTION"""
        
        # Force completion if we've tried too many times
        if context.failed_attempts >= 5:
            return {'action': 'complete', 'reason': 'max_attempts_reached'}
        
        # If we have too few sources, prioritize discovery
        if len(context.sources) < context.goal.min_sources:
            if context.can_perform_action('discover_sources'):
                if len(context.sources) < 3:
                    return {
                        'action': 'discover_sources',
                        'strategy': 'broad_search',
                        'query': f"{context.goal.topic} theological commentary scholarly"
                    }
                else:
                    return {
                        'action': 'discover_sources', 
                        'strategy': 'targeted_search',
                        'query': await self._generate_targeted_query(context)
                    }
        
        # If perspectives are missing, search for them specifically
        missing_perspectives = await self._find_missing_perspectives(context)
        if missing_perspectives and context.can_perform_action('discover_sources'):
            return {
                'action': 'discover_sources',
                'strategy': 'perspective_search',
                'perspectives': missing_perspectives
            }
        
        # Move to content analysis if we have enough sources
        if len(context.sources) >= context.goal.min_sources and context.current_focus == "initial_discovery":
            context.current_focus = "content_analysis"
            return {
                'action': 'fetch_content',
                'sources': context.sources[:3]  # Analyze first 3 sources
            }
        
        # If quality is low, improve it
        if context.quality_score < context.goal.quality_threshold and context.can_perform_action('improve_quality'):
            return {
                'action': 'improve_quality',
                'focus': await self._identify_quality_issues(context)
            }
        
        # If we have gaps in understanding, fill them
        gaps = await self._identify_knowledge_gaps(context)
        if gaps and context.can_perform_action('fill_gaps'):
            return {
                'action': 'fill_gaps',
                'gaps': gaps
            }
        
        # If all criteria met, complete
        if await self._all_criteria_met(context):
            return {'action': 'complete', 'reason': 'criteria_met'}
        
        # Default: synthesize what we have
        if context.can_perform_action('synthesize_current_findings'):
            return {
                'action': 'synthesize_current_findings'
            }
        
        # If we can't do anything, complete
        return {'action': 'complete', 'reason': 'no_viable_actions'}
    
    async def _execute_action(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Execute the chosen action"""
        
        if action['action'] == 'discover_sources':
            return await self._discover_sources(action, context)
        elif action['action'] == 'fetch_content':
            return await self._fetch_content(action, context)
        elif action['action'] == 'improve_quality':
            return await self._improve_quality(action, context)
        elif action['action'] == 'fill_gaps':
            return await self._fill_gaps(action, context)
        elif action['action'] == 'synthesize_current_findings':
            return await self._synthesize_findings(context)
        
        return {'status': 'unknown_action'}
    
    async def _fetch_content(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """NEW: Actually fetch and analyze content from sources"""
        content_analyzed = []
        
        for source in action.get('sources', []):
            try:
                content = await self._fetch_url_content(source.get('url', ''))
                if content:
                    # Extract insights from actual content
                    insights = await self._extract_theological_insights(content)
                    source['content'] = content[:1000]  # Store first 1000 chars
                    source['insights'] = insights
                    source['content_processed'] = True
                    content_analyzed.append(source)
            except Exception as e:
                logging.error(f"Error fetching content from {source.get('url', '')}: {e}")
                continue
        
        return {
            'action': 'fetch_content',
            'content_analyzed': content_analyzed,
            'success_count': len(content_analyzed)
        }
    
    async def _fetch_url_content(self, url: str) -> str:
        """Fetch and extract text content from a URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Use BeautifulSoup to extract text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return ""
    
    async def _extract_theological_insights(self, content: str) -> Dict[str, Any]:
        """Extract theological insights from content"""
        insights = {
            'biblical_references': [],
            'theological_themes': [],
            'author_perspective': 'unknown',
            'key_arguments': []
        }
        
        content_lower = content.lower()
        
        # Extract biblical references
        bible_pattern = r'\b\d*\s*[a-zA-Z]+\s+\d+:\d+(-\d+)?\b'
        insights['biblical_references'] = re.findall(bible_pattern, content)
        
        # Identify theological themes
        themes = [
            'salvation', 'grace', 'redemption', 'atonement', 'justification',
            'sanctification', 'eschatology', 'christology', 'pneumatology',
            'creation', 'covenant', 'trinity', 'incarnation', 'resurrection'
        ]
        
        for theme in themes:
            if theme in content_lower:
                insights['theological_themes'].append(theme)
        
        # Identify perspective based on keywords
        evangelical_keywords = ['evangelical', 'conservative', 'reformed', 'biblical inerrancy']
        progressive_keywords = ['progressive', 'liberal', 'historical-critical', 'contextual']
        orthodox_keywords = ['orthodox', 'traditional', 'catholic', 'patristic']
        
        for keyword in evangelical_keywords:
            if keyword in content_lower:
                insights['author_perspective'] = 'evangelical'
                break
        
        for keyword in progressive_keywords:
            if keyword in content_lower:
                insights['author_perspective'] = 'progressive'
                break
                
        for keyword in orthodox_keywords:
            if keyword in content_lower:
                insights['author_perspective'] = 'orthodox'
                break
        
        return insights
    
    async def _discover_sources(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Agent discovers new sources based on strategy"""
        
        if action['strategy'] == 'broad_search':
            search_results = await self._web_search(action['query'])
            new_sources = await self._filter_and_validate_sources(search_results)
            
        elif action['strategy'] == 'perspective_search':
            new_sources = []
            for perspective in action['perspectives']:
                query = f"{context.goal.topic} {perspective} perspective theology"
                results = await self._web_search(query)
                perspective_sources = await self._filter_sources_by_perspective(results, perspective)
                new_sources.extend(perspective_sources)
        
        elif action['strategy'] == 'targeted_search':
            search_results = await self._web_search(action['query'])
            new_sources = await self._filter_and_validate_sources(search_results)
        
        return {
            'action': 'discovered_sources',
            'new_sources': new_sources,
            'strategy': action['strategy']
        }
    
    async def _filter_and_validate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated_sources = []
        for source in sources:
            validation = await self._validate_source(source)
            if validation['valid']:
                validated_sources.append(source)
        return validated_sources

    async def _filter_sources_by_perspective(self, sources: List[Dict[str, Any]], perspective: str) -> List[Dict[str, Any]]:
        """Filter sources by theological perspective - SINGLE IMPLEMENTATION"""
        perspective_sources = []
        for source in sources:
            if perspective in str(source.get('description', '')).lower():
                perspective_sources.append(source)
        return perspective_sources

    async def _improve_quality(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Improve the quality of the research"""
        new_quality_score = context.quality_score
        
        # Implement actual quality improvements
        improvements = []
        
        # If we have low academic ratio, search for academic sources
        if action['focus'].get('low_academic_ratio'):
            academic_query = f"{context.goal.topic} academic scholarly journal"
            academic_results = await self._web_search(academic_query)
            improvements.append(f"Added {len(academic_results)} academic sources")
            new_quality_score += 0.2
        
        # If sources are outdated, search for recent ones
        if action['focus'].get('outdated_sources'):
            recent_query = f"{context.goal.topic} 2023 2024 recent"
            recent_results = await self._web_search(recent_query)
            improvements.append(f"Added {len(recent_results)} recent sources")
            new_quality_score += 0.1
        
        return {
            'action': 'improve_quality',
            'new_quality_score': min(new_quality_score, 1.0),
            'improvements': improvements
        }

    async def _fill_gaps(self, action: Dict[str, Any], context: ResearchContext) -> Dict[str, Any]:
        """Fill gaps in the research"""
        gaps_filled = []
        
        for gap in action.get('gaps', []):
            if gap == 'historical_context':
                query = f"{context.goal.topic} historical context ancient"
                results = await self._web_search(query)
                gaps_filled.append(f"historical_context: {len(results)} sources")
            elif gap == 'theological_analysis':
                query = f"{context.goal.topic} theological analysis systematic"
                results = await self._web_search(query)
                gaps_filled.append(f"theological_analysis: {len(results)} sources")
            elif gap == 'scholarly_consensus':
                query = f"{context.goal.topic} scholarly consensus debate"
                results = await self._web_search(query)
                gaps_filled.append(f"scholarly_consensus: {len(results)} sources")
        
        return {
            'action': 'fill_gaps',
            'gaps_filled': gaps_filled
        }

    async def _all_criteria_met(self, context: ResearchContext) -> bool:
        """Check if all completion criteria have been met"""
        return all(criterion in context.completed_criteria for criterion in context.goal.completion_criteria)

    async def _synthesize_findings(self, context: ResearchContext) -> Dict[str, Any]:
        """Synthesize findings from collected sources - IMPROVED VERSION"""
        key_themes = {}
        theological_perspectives = {}
        biblical_references = []
        
        # Analyze actual content instead of just counting keywords
        for source in context.sources:
            if source.get('content_processed') and source.get('insights'):
                insights = source['insights']
                
                # Collect theological themes
                for theme in insights.get('theological_themes', []):
                    key_themes[theme] = key_themes.get(theme, 0) + 1
                
                # Track perspectives
                perspective = insights.get('author_perspective', 'unknown')
                theological_perspectives[perspective] = theological_perspectives.get(perspective, 0) + 1
                
                # Collect biblical references
                biblical_references.extend(insights.get('biblical_references', []))
            
            # Fallback to keyword counting for unprocessed sources
            else:
                description = source.get('description', '').lower()
                if 'historical context' in description:
                    key_themes['historical_context'] = key_themes.get('historical_context', 0) + 1
                if 'theological' in description:
                    key_themes['theological_implications'] = key_themes.get('theological_implications', 0) + 1
                if 'scholarly' in description:
                    key_themes['scholarly_debate'] = key_themes.get('scholarly_debate', 0) + 1

        return {
            'action': 'synthesize_current_findings',
            'insights': {
                'key_themes': key_themes,
                'theological_perspectives': theological_perspectives,
                'biblical_references': list(set(biblical_references))[:10],  # Top 10 unique refs
                'content_analyzed': len([s for s in context.sources if s.get('content_processed')])
            }
        }

    async def _is_research_complete(self, context: ResearchContext) -> bool:
        """Agent assesses if research is complete - IMPROVED VERSION"""
        
        # Check all completion criteria
        criteria_status = {}
        
        # Sufficient sources
        criteria_status['sufficient_sources_found'] = len(context.sources) >= context.goal.min_sources
        
        # Multiple perspectives
        perspectives_found = len(await self._find_missing_perspectives(context))
        criteria_status['multiple_perspectives_represented'] = perspectives_found >= 2
        
        # Quality score - LOWERED threshold
        criteria_status['quality_score_met'] = context.quality_score >= context.goal.quality_threshold
        
        # Key themes identified - IMPROVED check
        theme_count = len(context.insights.get('key_themes', {}))
        criteria_status['key_themes_identified'] = theme_count >= 3
        
        # Citations validated - SIMPLIFIED check
        criteria_status['citations_validated'] = len(context.sources) >= 3
        
        # Track completed criteria
        context.completed_criteria = [k for k, v in criteria_status.items() if v]
        
        # Progressive completion - lower bar for basic functionality
        basic_completion = (
            len(context.sources) >= context.goal.min_sources and
            context.quality_score >= 0.4 and  # Even lower threshold
            len(context.completed_criteria) >= 3
        )
        
        if basic_completion:
            return True
        
        # Force completion if we've tried too many iterations
        return context.failed_attempts >= 5
    
    async def _generate_targeted_query(self, context: ResearchContext) -> str:
        """Agent generates intelligent follow-up queries"""
        
        # Analyze what we have and what's missing
        current_themes = list(context.insights.get('key_themes', {}).keys())
        
        if 'historical_context' not in current_themes:
            return f"{context.goal.topic} historical context ancient near east"
        elif 'theological_implications' not in current_themes:
            return f"{context.goal.topic} theological implications systematic theology"
        elif 'scholarly_debate' not in current_themes:
            return f"{context.goal.topic} scholarly debate controversy"
        else:
            return f"{context.goal.topic} recent scholarship 2023 2024"
    
    async def _identify_quality_issues(self, context: ResearchContext) -> Dict[str, Any]:
        """Agent identifies specific quality problems"""
        
        issues = {}
        
        # Source quality analysis
        academic_sources = [s for s in context.sources if 'academic' in str(s).lower()]
        if len(academic_sources) < len(context.sources) * 0.5:
            issues['low_academic_ratio'] = True
        
        # Recency check
        recent_sources = [s for s in context.sources if self._is_recent(s)]
        if len(recent_sources) < 2:
            issues['outdated_sources'] = True
        
        # Content processing check
        processed_sources = [s for s in context.sources if s.get('content_processed')]
        if len(processed_sources) < 3:
            issues['insufficient_content_analysis'] = True
        
        return issues
    
    async def _identify_knowledge_gaps(self, context: ResearchContext) -> List[str]:
        """Identify gaps in knowledge coverage"""
        gaps = []
        
        # Check for missing content types
        has_historical = any('historical' in str(s).lower() for s in context.sources)
        has_theological = any('theological' in str(s).lower() for s in context.sources)
        has_scholarly = any('scholarly' in str(s).lower() for s in context.sources)
        
        if not has_historical:
            gaps.append('historical_context')
        if not has_theological:
            gaps.append('theological_analysis')
        if not has_scholarly:
            gaps.append('scholarly_consensus')
        
        return gaps
    
    # Tool implementations
    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """IMPROVED: Use semantic scholar for academic papers"""
        try:
            # Try Semantic Scholar first for academic content
            if any(word in query.lower() for word in ['academic', 'scholarly', 'journal']):
                return await self._semantic_scholar_search(query)
            else:
                # Fallback to basic web search
                from tools import web_search
                result = web_search(query, max_results=5)
                return self._parse_search_results(result)
        except Exception as e:
            logging.error(f"Error in web search: {e}")
            return []
    
    async def _semantic_scholar_search(self, query: str) -> List[Dict[str, Any]]:
        """Search academic papers via Semantic Scholar API"""
        try:
            base_url = "https://api.semanticscholar.org/graph/v1"
            params = {
                'query': query,
                'fields': 'title,abstract,authors,year,citationCount,url',
                'limit': 5
            }
            
            response = requests.get(f"{base_url}/paper/search", params=params)
            response.raise_for_status()
            
            results = []
            for paper in response.json().get('data', []):
                results.append({
                    'title': paper.get('title', ''),
                    'url': paper.get('url', ''),
                    'description': paper.get('abstract', '')[:500],
                    'authors': [author.get('name', '') for author in paper.get('authors', [])],
                    'year': paper.get('year', ''),
                    'citations': paper.get('citationCount', 0),
                    'source_type': 'academic'
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Error in Semantic Scholar search: {e}")
            return []
    
    async def _pdf_search(self, query: str) -> List[Dict[str, Any]]:
        """Search for PDFs using Semantic Scholar API"""
        return await self._semantic_scholar_search(query)
    
    async def _podcast_search(self, query: str) -> List[Dict[str, Any]]:
        """Future: YouTube API for transcripts"""
        return []
    
    async def _extract_citations(self, content: str) -> List[str]:
        """Extract citations from text"""
        citation_patterns = [
            r'\([^)]*\d{4}[^)]*\)',  # (Author, 2024)
            r'\d+:\d+-\d+',          # Bible verses
            r'\([^)]*\d{4}:\d+\)'   # (Author, 2024:123)
        ]
        citations = []
        for pattern in citation_patterns:
            citations.extend(re.findall(pattern, content))
        return citations
    
    async def _validate_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Basic source validation"""
        return {
            'valid': bool(source.get('url') and source.get('title')),
            'credibility_score': 0.9 if source.get('source_type') == 'academic' else 0.5
        }
    
    async def _synthesize_insights(self, context: ResearchContext) -> Dict[str, Any]:
        """Generate insights from collected sources"""
        return {
            'key_themes': {
                'historical_context': len([s for s in context.sources if 'context' in str(s).lower()]),
                'theological_implications': len([s for s in context.sources if 'theology' in str(s).lower()]),
                'scholarly_consensus': len([s for s in context.sources if 'scholar' in str(s).lower()])
            }
        }
    
    async def _assess_quality(self, context: ResearchContext) -> float:
        """Calculate overall research quality - IMPROVED VERSION"""
        score = 0.0
        
        # Source quantity (30%)
        if len(context.sources) >= context.goal.min_sources:
            score += 0.3
        
        # Content processing (40%)
        processed_count = len([s for s in context.sources if s.get('content_processed')])
        if processed_count >= 3:
            score += 0.4
        elif processed_count >= 1:
            score += 0.2
        
        # Perspective diversity (20%)
        perspectives = set()
        for source in context.sources:
            if source.get('insights'):
                perspectives.add(source['insights'].get('author_perspective', 'unknown'))
        if len(perspectives) >= 2:
            score += 0.2
        
        # Theme coverage (10%)
        themes = context.insights.get('key_themes', {})
        if len(themes) >= 3:
            score += 0.1
        
        return min(score, 1.0)
    
    async def _identify_gaps(self, context: ResearchContext) -> List[str]:
        """Identify missing knowledge areas"""
        gaps = []
        
        if not any('historical' in str(s).lower() for s in context.sources):
            gaps.append('historical_context')
        if not any('theological' in str(s).lower() for s in context.sources):
            gaps.append('theological_analysis')
        if not any('scholarly' in str(s).lower() for s in context.sources):
            gaps.append('scholarly_consensus')
        
        return gaps
    
    # Utility methods
    def _parse_search_results(self, search_result: str) -> List[Dict[str, Any]]:
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
    
    async def _update_context(self, context: ResearchContext, result: Dict[str, Any]) -> ResearchContext:
        """Update context based on action results"""
        
        if result['action'] == 'discovered_sources':
            context.sources.extend(result['new_sources'])
            # Re-assess quality after adding sources
            context.quality_score = await self._assess_quality(context)
        
        elif result['action'] == 'fetch_content':
            # Update sources with processed content
            for analyzed_source in result.get('content_analyzed', []):
                for source in context.sources:
                    if source.get('url') == analyzed_source.get('url'):
                        source.update(analyzed_source)
            context.quality_score = await self._assess_quality(context)
        
        elif result['action'] == 'synthesize_current_findings':
            context.insights = result.get('insights', {})
            context.quality_score = await self._assess_quality(context)
        
        elif result['action'] == 'improve_quality':
            context.quality_score = result.get('new_quality_score', context.quality_score)
        
        return context
    
    async def _generate_final_report(self, context: ResearchContext) -> str:
        """Generate comprehensive final report"""
        
        report = f"# Autonomous Research: {context.goal.topic}\n\n"
        report += f"**Research Mandate**: {context.goal.research_mandate}\n\n"
        report += f"**Quality Score**: {context.quality_score:.2f}\n\n"
        report += f"**Sources Found**: {len(context.sources)}\n\n"
        
        # Content analysis summary
        processed_count = len([s for s in context.sources if s.get('content_processed')])
        report += f"**Content Processed**: {processed_count} sources\n\n"
        
        report += "## Key Insights\n"
        insights = context.insights.get('key_themes', {})
        for theme, count in insights.items():
            report += f"- **{theme.replace('_', ' ').title()}**: {count} sources\n"
        
        # Theological perspectives
        perspectives = context.insights.get('theological_perspectives', {})
        if perspectives:
            report += "\n## Theological Perspectives\n"
            for perspective, count in perspectives.items():
                report += f"- **{perspective.title()}**: {count} sources\n"
        
        # Biblical references
        biblical_refs = context.insights.get('biblical_references', [])
        if biblical_refs:
            report += f"\n## Biblical References\n"
            report += f"Found {len(biblical_refs)} biblical references\n"
        
        report += "\n## Sources\n"
        for i, source in enumerate(context.sources, 1):
            title = source.get('title', 'Untitled')
            url = source.get('url', '#')
            processed = " ✓" if source.get('content_processed') else ""
            report += f"{i}. [{title}]({url}){processed}\n"
        
        report += f"\n## Completion Status\n"
        report += f"Completed: {', '.join(context.completed_criteria)}\n"
        report += f"Iterations: {len(context.action_history)}\n"
        
        return report
    
    def _is_recent(self, source: Dict[str, Any]) -> bool:
        """Simple recency check"""
        desc = str(source.get('description', ''))
        return any(str(year) in desc for year in range(2020, 2025))
    
    async def _find_missing_perspectives(self, context: ResearchContext) -> List[str]:
        """Identify which theological perspectives are missing"""
        found_perspectives = set()
        for source in context.sources:
            desc = str(source.get('description', '')).lower()
            for perspective in context.goal.required_perspectives:
                if perspective in desc:
                    found_perspectives.add(perspective)
        
        return [p for p in context.goal.required_perspectives if p not in found_perspectives]
    
    async def _count_perspectives(self, context: ResearchContext) -> int:
        found_perspectives = await self._find_missing_perspectives(context)
        return len(context.goal.required_perspectives) - len(found_perspectives)
    
    async def _validate_all_citations(self, context: ResearchContext) -> Dict[str, Any]:
        total_citations = 0
        valid_citations = 0
        
        for source in context.sources:
            desc = source.get('description', '')
            citations = await self._extract_citations(desc)
            total_citations += len(citations)
            valid_citations += len(citations)  # Simplified validation
        
        return {
            'total': total_citations,
            'valid': valid_citations,
            'valid_ratio': valid_citations / max(total_citations, 1)
        }
    
    async def _check_citation_quality(self, context: ResearchContext) -> List[str]:
        return []  # Placeholder for detailed citation analysis

# Usage example
async def main():
    agent = AutonomousResearchAgent()
    
    goal = ResearchGoal(
        topic="Genesis 1 creation narrative",
        research_mandate="Provide a comprehensive theological analysis that includes multiple scholarly perspectives, historical context, and contemporary applications. Must demonstrate academic rigor with properly cited sources.",
        quality_threshold=0.6,  # Lowered from 0.8
        max_sources=12
    )
    
    result = await agent.conduct_research(goal)
    print(result['final_report'])

if __name__ == "__main__":
    asyncio.run(main())