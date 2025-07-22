# AI Research Agent

A powerful AI-powered research system using Moonshot Kimi model for autonomous research and analysis.

## 🚀 Features

- **Real AI Autonomy**: Uses Moonshot Kimi model for actual decision-making and reasoning
- **Multi-Step Research**: AI plans and executes research strategies autonomously
- **Web Search Integration**: Brave Search API for comprehensive information gathering
- **Source Analysis**: AI-powered content analysis and credibility assessment
- **Quality Control**: Automated quality scoring and validation
- **Research Memory**: Persistent context and citation tracking
- **Web Interface**: Modern, responsive UI for easy interaction

## 🏗️ Architecture

### Core Components

1. **AI Research Coordinator** (`enhanced_autonomous_researcher.py`)
   - Uses Moonshot Kimi model for autonomous decision-making
   - Plans research strategies based on query analysis
   - Orchestrates tool usage and research flow
   - Synthesizes findings with AI reasoning

2. **Research Tools** (`tools.py`)
   - Web search via Brave API
   - Content extraction and analysis
   - Note saving and management
   - Health monitoring

3. **Web Application** (`app_agents.py`)
   - Flask-based REST API
   - Real-time research status updates
   - Session management
   - Error handling

4. **Frontend Interface** (`templates/`, `static/`)
   - Modern responsive design
   - Real-time progress tracking
   - Agent activity visualization
   - Markdown rendering

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- Moonshot AI API key
- Brave Search API key

### Installation

1. **Clone and setup**:
   ```bash
   cd RESEARCH_AGENT
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys:
   # MOONSHOT_API_KEY=your_moonshot_key
   # BRAVE_API_KEY=your_brave_key
   ```

3. **Test the system**:
   ```bash
   python test_ai_agent.py
   ```

4. **Run the application**:
   ```bash
   python app_agents.py
   ```

5. **Access the interface**:
   Open http://localhost:5023 in your browser

## 🔧 Configuration

### Environment Variables

- `MOONSHOT_API_KEY`: Your Moonshot AI API key (required)
- `BRAVE_API_KEY`: Your Brave Search API key (required)
- `PORT`: Server port (default: 5023)
- `DEBUG`: Enable debug mode (default: false)

### API Keys

1. **Moonshot AI**: Get your key from [Moonshot Platform](https://platform.moonshot.ai/)
2. **Brave Search**: Get your key from [Brave Search API](https://api.search.brave.com/)

## 🧠 How It Works

### Research Process

1. **Query Analysis**: AI analyzes the research query and creates a comprehensive plan
2. **Strategy Planning**: Determines information sources, methodology, and quality criteria
3. **Autonomous Execution**: AI decides which tools to use and when
4. **Source Collection**: Web searches with intelligent query generation
5. **Content Analysis**: AI-powered analysis of collected sources
6. **Quality Assessment**: Continuous quality scoring and validation
7. **Synthesis**: AI generates comprehensive final reports

### AI Decision Making

The system uses the Moonshot Kimi model to:
- Plan research strategies
- Generate targeted search queries
- Assess source credibility
- Identify knowledge gaps
- Synthesize findings
- Generate final reports

## 📊 API Endpoints

### Research API

- `POST /api/research`: Start new research
  ```json
  {
    "query": "Your research question"
  }
  ```

- `GET /api/research/{session_id}/status`: Get research status
  ```json
  {
    "status": "running|completed|error",
    "progress": 75,
    "current_step": "Analyzing sources",
    "final_report": "...",
    "sources": 5,
    "quality_score": 0.8
  }
  ```

- `GET /api/health`: System health check

## 🔍 Usage Examples

### Basic Research
```python
from enhanced_autonomous_researcher import EnhancedAutonomousResearchAgent

agent = EnhancedAutonomousResearchAgent()
result = await agent.conduct_research("What are the latest developments in quantum computing?")
print(result['final_report'])
```

### Web Interface
1. Open http://localhost:5023
2. Enter your research question
3. Watch the AI agent work autonomously
4. Review the comprehensive research report

## 🧪 Testing

Run the test suite to verify everything works:

```bash
python test_ai_agent.py
```

Tests include:
- Moonshot API connection
- Web search functionality
- Full AI research agent workflow

## 🔧 Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Verify your API keys in `.env`
   - Check key permissions and quotas

2. **Search Failures**:
   - Verify Brave API key
   - Check internet connectivity

3. **AI Response Issues**:
   - Verify Moonshot API key
   - Check API rate limits

### Debug Mode

Enable debug logging:
```bash
export DEBUG=true
python app_agents.py
```

## 🆚 Improvements Over Previous System

### Before (Fake Autonomous System)
- ❌ No real AI decision-making
- ❌ Hardcoded research patterns
- ❌ Simulated agent activity
- ❌ Basic keyword matching
- ❌ No real content analysis

### After (Real AI Research Agent)
- ✅ Moonshot Kimi model for real autonomy
- ✅ Dynamic research strategy planning
- ✅ Intelligent tool orchestration
- ✅ AI-powered content analysis
- ✅ Quality assessment and validation
- ✅ Comprehensive report generation

## 🚀 Future Enhancements

- [ ] Academic paper search (arXiv, PubMed)
- [ ] PDF document processing
- [ ] Multi-language research support
- [ ] Research collaboration features
- [ ] Advanced citation analysis
- [ ] Knowledge graph visualization

## 📝 License

This project is for research and educational purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Built with ❤️ using Moonshot Kimi AI**
