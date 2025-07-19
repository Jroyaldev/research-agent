"""
Task Graph Schema for Research Planning
Provides structured task planning with dependency management
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import uuid

@dataclass
class Task:
    """Individual task in the research pipeline"""
    id: str
    tool: str
    args: Dict[str, Any]
    depends_on: List[str]
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

@dataclass
class ResearchGraph:
    """Complete research task graph"""
    topic: str
    tasks: List[Task]
    graph_id: str = ""
    status: str = "planning"  # planning, executing, completed, failed
    created_at: str = ""
    
    def __post_init__(self):
        if not self.graph_id:
            self.graph_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

class TaskPlanner:
    """Generates task graphs for research queries"""
    
    def __init__(self):
        self.planning_templates = {
            "biblical_exegesis": [
                {
                    "id": "SEARCH_PRIMARY",
                    "tool": "web_search",
                    "args": {"query": "{topic} scholarly exegesis 2020..2025", "max_results": 5},
                    "depends_on": []
                },
                {
                    "id": "SEARCH_SECONDARY",
                    "tool": "web_search", 
                    "args": {"query": "{topic} ancient near east context intertextuality", "max_results": 3},
                    "depends_on": ["SEARCH_PRIMARY"]
                },
                {
                    "id": "FETCH_PDFS",
                    "tool": "get_pdf",
                    "args": {"urls_from": "SEARCH_PRIMARY"},
                    "depends_on": ["SEARCH_PRIMARY", "SEARCH_SECONDARY"]
                },
                {
                    "id": "EXTRACT_CITATIONS",
                    "tool": "extract_metadata",
                    "args": {"pdf_ids_from": "FETCH_PDFS"},
                    "depends_on": ["FETCH_PDFS"]
                },
                {
                    "id": "CRITICAL_ANALYSIS",
                    "tool": "synthesize_research",
                    "args": {"sources_from": "EXTRACT_CITATIONS", "topic": "{topic}"},
                    "depends_on": ["EXTRACT_CITATIONS"]
                },
                {
                    "id": "VALIDATE_CITATIONS",
                    "tool": "hallucination_check",
                    "args": {"content_from": "CRITICAL_ANALYSIS", "citations_from": "EXTRACT_CITATIONS"},
                    "depends_on": ["CRITICAL_ANALYSIS"]
                },
                {
                    "id": "FINAL_REPORT",
                    "tool": "save_note",
                    "args": {"filename": "{safe_topic}.md", "content_from": "VALIDATE_CITATIONS"},
                    "depends_on": ["VALIDATE_CITATIONS"]
                }
            ]
        }
    
    def create_plan(self, topic: str, plan_type: str = "biblical_exegesis") -> ResearchGraph:
        """Generate a task graph for the given topic"""
        if plan_type not in self.planning_templates:
            plan_type = "biblical_exegesis"
            
        template = self.planning_templates[plan_type]
        tasks = []
        
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_topic = safe_topic.replace(' ', '_')
        
        for task_template in template:
            task_dict = task_template.copy()
            
            # Fill in template variables
            for key, value in task_dict["args"].items():
                if isinstance(value, str):
                    task_dict["args"][key] = value.format(topic=topic, safe_topic=safe_topic)
            
            task = Task(
                id=task_dict["id"],
                tool=task_dict["tool"],
                args=task_dict["args"],
                depends_on=task_dict["depends_on"]
            )
            tasks.append(task)
        
        return ResearchGraph(topic=topic, tasks=tasks)
    
    def get_ready_tasks(self, graph: ResearchGraph) -> List[Task]:
        """Get tasks that are ready to run (all dependencies completed)"""
        ready_tasks = []
        
        for task in graph.tasks:
            if task.status != "pending":
                continue
                
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in task.depends_on:
                dep_task = next((t for t in graph.tasks if t.id == dep_id), None)
                if not dep_task or dep_task.status != "completed":
                    dependencies_met = False
                    break
            
            if dependencies_met:
                ready_tasks.append(task)
        
        return ready_tasks
    
    def save_graph(self, graph: ResearchGraph, filepath: str):
        """Save task graph to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(graph), f, indent=2)
    
    def load_graph(self, filepath: str) -> ResearchGraph:
        """Load task graph from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        tasks = [Task(**task_data) for task_data in data["tasks"]]
        return ResearchGraph(
            topic=data["topic"],
            tasks=tasks,
            graph_id=data["graph_id"],
            status=data["status"],
            created_at=data["created_at"]
        )