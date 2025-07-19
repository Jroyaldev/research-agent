class ResearchApp {
    constructor() {
        this.currentSession = null;
        this.pollInterval = null;
        this.startTime = null;
        
        this.initializeElements();
        this.bindEvents();
    }
    
    initializeElements() {
        this.elements = {
            queryInput: document.getElementById('research-query'),
            researchBtn: document.getElementById('research-btn'),
            clearBtn: document.getElementById('clear-btn'),
            statusSection: document.getElementById('research-status'),
            resultSection: document.getElementById('research-result'),
            errorSection: document.getElementById('error-message'),
            currentQuery: document.getElementById('current-query'),
            elapsedTime: document.getElementById('elapsed-time'),
            resultText: document.getElementById('result-text'),
            copyBtn: document.getElementById('copy-btn'),
            newResearchBtn: document.getElementById('new-research-btn'),
            retryBtn: document.getElementById('retry-btn')
        };
    }
    
    bindEvents() {
        this.elements.researchBtn.addEventListener('click', () => this.startResearch());
        this.elements.clearBtn.addEventListener('click', () => this.clearQuery());
        this.elements.copyBtn.addEventListener('click', () => this.copyResult());
        this.elements.newResearchBtn.addEventListener('click', () => this.resetApp());
        this.elements.retryBtn.addEventListener('click', () => this.retryResearch());
        
        this.elements.queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.startResearch();
            }
        });
    }
    
    async startResearch() {
        const query = this.elements.queryInput.value.trim();
        
        if (!query) {
            this.showError('Please enter a research question.');
            return;
        }
        
        this.hideAllSections();
        this.showStatus(query);
        
        try {
            const response = await fetch('/api/research', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    query: query,
                    research_type: 'biblical_exegesis' 
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.showError(data.error);
                return;
            }
            
            this.currentSession = data.session_id;
            this.startTime = Date.now();
            this.startPolling();
            
        } catch (error) {
            this.showError('Failed to start research. Please check your connection and try again.');
            console.error('Error:', error);
        }
    }
    
    startPolling() {
        this.pollInterval = setInterval(() => {
            this.pollStatus();
            this.updateTimer();
        }, 2000);
    }
    
    async pollStatus() {
        if (!this.currentSession) return;
        
        try {
            const response = await fetch(`/api/research/${this.currentSession}/status`);
            const data = await response.json();
            
            if (data.error) {
                this.showError(data.error);
                this.stopPolling();
                return;
            }
            
            // Update agent activity display
            this.updateAgentDisplay(data);
            
            if (data.status === 'completed') {
                const content = this.generateActualContent(data.query || '', data);
                this.showResult(content);
                this.stopPolling();
                this.hideAgentDisplay();
            } else if (data.status === 'error') {
                this.showError(data.error);
                this.stopPolling();
                this.hideAgentDisplay();
            }
            
            // Update progress
            this.updateProgressBar(data.progress || 0);
            
        } catch (error) {
            this.showError('Failed to get research status.');
            this.stopPolling();
            console.error('Error:', error);
        }
    }
    
    updateAgentDisplay(data) {
        const statusSection = this.elements.statusSection;
        const agents = data.agents || [];
        const currentAgent = data.current_agent;
        
        if (agents.length > 0 || currentAgent) {
            let agentHTML = '<div class="agent-activity">';
            
            // Show all agent activities
            agents.forEach(agent => {
                agentHTML += `
                    <div class="agent-card" style="border-left: 4px solid ${agent.color}; margin-bottom: 10px;">
                        <div class="agent-header">
                            <span class="agent-icon">${agent.icon}</span>
                            <span class="agent-name">${agent.name}</span>
                            <span class="agent-status-badge ${agent.status}">${agent.status}</span>
                        </div>
                        <div class="agent-message">${agent.message}</div>
                        <div class="agent-timestamp">${new Date(agent.timestamp).toLocaleTimeString()}</div>
                    </div>
                `;
            });
            
            // Also show current agent if not in the list
            if (currentAgent && !agents.find(a => a.agent === currentAgent.agent)) {
                agentHTML += `
                    <div class="agent-card" style="border-left: 4px solid ${currentAgent.color}; margin-bottom: 10px;">
                        <div class="agent-header">
                            <span class="agent-icon">${currentAgent.icon}</span>
                            <span class="agent-name">${currentAgent.name}</span>
                            <span class="agent-status-badge ${currentAgent.status}">${currentAgent.status}</span>
                        </div>
                        <div class="agent-message">${currentAgent.message}</div>
                        <div class="agent-timestamp">${new Date(currentAgent.timestamp).toLocaleTimeString()}</div>
                    </div>
                `;
            }
            
            agentHTML += '</div>';
            
            // Add to status display
            const agentDisplay = statusSection.querySelector('.agent-display') || 
                                this.createAgentDisplay(statusSection);
            agentDisplay.innerHTML = agentHTML;
        }
    }
    
    createAgentDisplay(statusSection) {
        const agentDisplay = document.createElement('div');
        agentDisplay.className = 'agent-display';
        statusSection.appendChild(agentDisplay);
        return agentDisplay;
    }
    
    hideAgentDisplay() {
        const agentDisplay = document.querySelector('.agent-display');
        if (agentDisplay) {
            agentDisplay.style.display = 'none';
        }
    }
    
    updateProgressBar(percent) {
        const progressBar = document.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.style.transition = 'width 0.5s ease';
        }
    }
    
    generateActualContent(query, data) {
        // Use AI-generated final report if available
        if (data.final_report) {
            return this.enhanceReportWithMetadata(data.final_report, data);
        }
        
        // Fallback content generation
        let content = `# AI Research Results: ${query}\n\n`;
        content += `**Generated by**: Moonshot Kimi AI Research Agent\n`;
        content += `**Date**: ${new Date().toLocaleDateString()}\n`;
        content += `**Quality Score**: ${data.quality_score || 'N/A'}\n`;
        content += `**Sources Found**: ${data.sources || 0}\n\n`;
        
        // Add biblical research indicator
        if (data.is_biblical_query) {
            content += `🔍 **Enhanced Biblical Research Mode** - This query was detected as biblical content and includes specialized podcast search.\n\n`;
        }
        
        content += `## Research Summary\n`;
        content += `This research was conducted using an AI-powered autonomous research agent that:\n`;
        content += `- Created a comprehensive research plan\n`;
        content += `- Executed web searches using advanced queries\n`;
        
        if (data.is_biblical_query) {
            content += `- Searched biblical study podcasts for relevant episodes\n`;
        }
        
        content += `- Analyzed sources for credibility and relevance\n`;
        content += `- Synthesized findings using AI reasoning\n\n`;
        
        if (data.sources && data.sources > 0) {
            content += `## Key Findings\n`;
            content += `The AI research agent successfully identified ${data.sources} relevant sources`;
            
            if (data.podcast_episodes_found > 0) {
                content += ` including ${data.podcast_episodes_found} biblical podcast episodes`;
            }
            
            content += ` and conducted comprehensive analysis.\n\n`;
        }
        
        content += `## Research Methodology\n`;
        content += `This research utilized the Moonshot Kimi model for autonomous decision-making, combined with web search capabilities`;
        
        if (data.is_biblical_query) {
            content += ` and specialized biblical podcast search`;
        }
        
        content += ` to gather and analyze information systematically.\n\n`;
        
        content += `## Note\n`;
        content += `This research was conducted by an AI agent. For academic or professional use, please verify findings with primary sources.`;
        
        return content;
    }
    
    enhanceReportWithMetadata(report, data) {
        // Add biblical research indicator at the top if applicable
        if (data.is_biblical_query && data.podcast_episodes_found > 0) {
            const indicator = `\n🎧 **Enhanced Biblical Research** - Found ${data.podcast_episodes_found} relevant podcast episodes from biblical study podcasts\n\n`;
            
            // Insert after the first heading
            const lines = report.split('\n');
            const firstHeadingIndex = lines.findIndex(line => line.startsWith('#'));
            
            if (firstHeadingIndex !== -1 && firstHeadingIndex < lines.length - 1) {
                lines.splice(firstHeadingIndex + 1, 0, indicator);
                return lines.join('\n');
            } else {
                return indicator + report;
            }
        }
        
        return report;
    }
    
    updateProgress(percent) {
        const progressBar = document.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
    }
    
    updateTimer() {
        if (this.startTime) {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            this.elements.elapsedTime.textContent = `${elapsed}s`;
        }
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    showStatus(query) {
        this.hideAllSections();
        this.elements.currentQuery.textContent = query;
        this.elements.statusSection.classList.remove('hidden');
    }
    
    showResult(result) {
        this.hideAllSections();
        this.elements.resultText.innerHTML = this.renderMarkdown(result);
        this.elements.resultSection.classList.remove('hidden');
        
        // Add copy functionality
        this.elements.copyBtn.style.display = 'flex';
    }
    
    showError(message) {
        this.hideAllSections();
        document.getElementById('error-text').textContent = message;
        this.elements.errorSection.classList.remove('hidden');
    }
    
    hideAllSections() {
        this.elements.statusSection.classList.add('hidden');
        this.elements.resultSection.classList.add('hidden');
        this.elements.errorSection.classList.add('hidden');
    }
    
    clearQuery() {
        this.elements.queryInput.value = '';
        this.elements.queryInput.focus();
    }
    
    resetApp() {
        this.elements.queryInput.value = '';
        this.hideAllSections();
        this.currentSession = null;
        this.startTime = null;
        this.stopPolling();
    }
    
    retryResearch() {
        this.hideAllSections();
        this.startResearch();
    }
    
    async copyResult() {
        const resultText = this.elements.resultText.textContent;
        
        try {
            await navigator.clipboard.writeText(resultText);
            
            // Show success feedback
            const originalText = this.elements.copyBtn.innerHTML;
            this.elements.copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            this.elements.copyBtn.style.background = 'var(--success)';
            
            setTimeout(() => {
                this.elements.copyBtn.innerHTML = originalText;
                this.elements.copyBtn.style.background = '';
            }, 2000);
            
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    }
    
    renderMarkdown(text) {
        // Basic markdown to HTML conversion
        let html = text
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(.+)$/gm, '<p>$1</p>');
        
        return html;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ResearchApp();
});
