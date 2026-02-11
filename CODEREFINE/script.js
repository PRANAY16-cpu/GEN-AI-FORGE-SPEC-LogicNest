const API_URL = 'http://localhost:8000';

let currentIssues = [];
let currentSeverityFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    animateHeroCode();
    setupSmoothScroll();
    updateLineNumbers();
}

function setupEventListeners() {
    document.getElementById('analyzeBtn').addEventListener('click', handleAnalyze);
    document.getElementById('pasteBtn').addEventListener('click', handlePaste);
    document.getElementById('clearBtn').addEventListener('click', handleClear);
    document.getElementById('uploadBtn').addEventListener('click', () => {
        document.getElementById('fileInput').click();
    });
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
    document.getElementById('codeInput').addEventListener('input', handleCodeInput);
    document.getElementById('copyOptimizedBtn').addEventListener('click', handleCopyOptimized);
    document.getElementById('exportBtn').addEventListener('click', handleExport);
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => handleTabChange(btn.dataset.tab));
    });
    
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => handleSeverityFilter(btn.dataset.severity));
    });
    
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    hamburger.addEventListener('click', () => {
        navMenu.classList.toggle('active');
    });
    
    document.querySelectorAll('.nav-menu a').forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
        });
    });
}

function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

function animateHeroCode() {
    const codeElement = document.getElementById('animatedCode');
    const codeSnippet = `function analyzeCode(input) {
  const ai = new CodeRefine();
  const results = ai.review(input);
  
  return {
    quality: results.score,
    issues: results.bugs,
    optimized: results.code
  };
}`;
    
    let index = 0;
    const speed = 30;
    
    function typeWriter() {
        if (index < codeSnippet.length) {
            codeElement.textContent += codeSnippet.charAt(index);
            index++;
            setTimeout(typeWriter, speed);
        } else {
            setTimeout(() => {
                codeElement.textContent = '';
                index = 0;
                typeWriter();
            }, 3000);
        }
    }
    
    typeWriter();
}

function handleCodeInput(e) {
    const code = e.target.value;
    const lines = code.split('\n').length;
    const chars = code.length;
    
    document.querySelector('.char-count').textContent = `${chars} characters | ${lines} lines`;
    updateLineNumbers();
}

function updateLineNumbers() {
    const textarea = document.getElementById('codeInput');
    const lineNumbers = document.getElementById('lineNumbers');
    const lines = textarea.value.split('\n').length;
    
    let lineNumbersHTML = '';
    for (let i = 1; i <= lines; i++) {
        lineNumbersHTML += `${i}\n`;
    }
    lineNumbers.textContent = lineNumbersHTML;
}

async function handlePaste() {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById('codeInput').value = text;
        handleCodeInput({ target: document.getElementById('codeInput') });
    } catch (err) {
        console.error('Failed to read clipboard:', err);
    }
}

function handleClear() {
    document.getElementById('codeInput').value = '';
    handleCodeInput({ target: document.getElementById('codeInput') });
}

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            document.getElementById('codeInput').value = event.target.result;
            handleCodeInput({ target: document.getElementById('codeInput') });
        };
        reader.readAsText(file);
    }
}

async function handleAnalyze() {
    const codeInput = document.getElementById('codeInput').value.trim();
    
    if (!codeInput) {
        showError('Please enter some code to analyze!');
        return;
    }
    
    const language = document.getElementById('languageSelect').value;
    const depth = document.getElementById('analysisDepth').value;
    const checkSecurity = document.getElementById('checkSecurity').checked;
    const checkPerformance = document.getElementById('checkPerformance').checked;
    const checkBestPractices = document.getElementById('checkBestPractices').checked;
    
    hideError();
    hideResults();
    showLoading();
    disableButton(true);
    
    try {
        const response = await fetch(`${API_URL}/review`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: codeInput,
                language: language,
                depth: depth,
                check_security: checkSecurity,
                check_performance: checkPerformance,
                check_best_practices: checkBestPractices
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to analyze code');
        }
        
        const data = await response.json();
        displayResults(data, codeInput);
        
    } catch (error) {
        console.error('Error:', error);
        showError(`Error: ${error.message}`);
    } finally {
        hideLoading();
        disableButton(false);
    }
}

function displayResults(data, originalCode) {
    document.getElementById('detectedLang').textContent = data.detected_language;
    document.getElementById('lineCount').textContent = data.line_count || '-';
    document.getElementById('complexity').textContent = data.complexity || 'Medium';
    
    const score = data.quality_score;
    updateScoreDisplay(score);
    
    document.getElementById('securityScore').textContent = data.security_score + '%' || '-';
    document.getElementById('performanceScore').textContent = data.performance_score + '%' || '-';
    document.getElementById('maintainabilityScore').textContent = data.maintainability_score + '%' || '-';
    
    currentIssues = data.issues || [];
    displayIssues(currentIssues);
    
    document.getElementById('optimizedCode').textContent = data.optimized_code;
    document.getElementById('originalCodeDisplay').textContent = originalCode;
    document.getElementById('optimizedCodeDisplay').textContent = data.optimized_code;
    
    const originalLines = originalCode.split('\n').length;
    const optimizedLines = data.optimized_code.split('\n').length;
    const linesReduced = originalLines - optimizedLines;
    
    document.getElementById('linesReduced').textContent = linesReduced > 0 ? `-${linesReduced}` : '0';
    document.getElementById('complexityReduced').textContent = data.complexity_reduction || '0%';
    document.getElementById('issuesFixed').textContent = currentIssues.filter(i => i.severity === 'critical').length;
    
    const explanationDiv = document.getElementById('explanation');
    explanationDiv.innerHTML = formatExplanation(data.explanation);
    
    showResults();
    
    document.getElementById('resultsSection').scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

function updateScoreDisplay(score) {
    const scoreElement = document.getElementById('qualityScore');
    const scoreRing = document.getElementById('scoreRing');
    const scoreGrade = document.getElementById('scoreGrade');
    
    scoreElement.textContent = score;
    
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (score / 100) * circumference;
    scoreRing.style.strokeDashoffset = offset;
    
    let grade, color;
    if (score >= 90) {
        grade = 'A+';
        color = '#10b981';
    } else if (score >= 80) {
        grade = 'A';
        color = '#10b981';
    } else if (score >= 70) {
        grade = 'B';
        color = '#3b82f6';
    } else if (score >= 60) {
        grade = 'C';
        color = '#f59e0b';
    } else {
        grade = 'D';
        color = '#ef4444';
    }
    
    scoreGrade.textContent = grade;
    scoreRing.style.stroke = color;
}

function displayIssues(issues) {
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';
    
    const filteredIssues = currentSeverityFilter === 'all' 
        ? issues 
        : issues.filter(i => i.severity === currentSeverityFilter);
    
    document.getElementById('issuesCount').textContent = filteredIssues.length;
    
    if (filteredIssues.length === 0) {
        issuesList.innerHTML = '<div class="issue-item info"><p>No issues found matching the current filter!</p></div>';
        return;
    }
    
    filteredIssues.forEach(issue => {
        const issueElement = document.createElement('div');
        issueElement.className = `issue-item ${issue.severity}`;
        issueElement.innerHTML = `
            <div class="issue-header">
                <div class="issue-title">
                    <i class="fas fa-${getSeverityIcon(issue.severity)}"></i>
                    ${issue.title}
                </div>
                <span class="severity-badge ${issue.severity}">${issue.severity}</span>
            </div>
            <p class="issue-description">${issue.description}</p>
            ${issue.location ? `<span class="issue-location">Line ${issue.location}</span>` : ''}
        `;
        issuesList.appendChild(issueElement);
    });
}

function getSeverityIcon(severity) {
    const icons = {
        critical: 'exclamation-triangle',
        warning: 'exclamation-circle',
        info: 'info-circle'
    };
    return icons[severity] || 'info-circle';
}

function formatExplanation(explanation) {
    const sections = explanation.split('\n\n');
    let html = '';
    
    sections.forEach(section => {
        if (section.startsWith('**') || section.startsWith('##')) {
            const title = section.replace(/\*\*|##/g, '').trim();
            html += `<h3>${title}</h3>`;
        } else if (section.includes('\n- ') || section.includes('\n* ')) {
            const items = section.split('\n').filter(line => line.trim());
            html += '<ul>';
            items.forEach(item => {
                if (item.startsWith('- ') || item.startsWith('* ')) {
                    html += `<li>${item.substring(2)}</li>`;
                }
            });
            html += '</ul>';
        } else {
            const formatted = section
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            html += `<p>${formatted}</p>`;
        }
    });
    
    return html;
}

function handleTabChange(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    event.target.closest('.tab-btn').classList.add('active');
    document.getElementById(`${tab}Tab`).classList.add('active');
}

function handleSeverityFilter(severity) {
    currentSeverityFilter = severity;
    
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    displayIssues(currentIssues);
}

function handleCopyOptimized() {
    const optimizedCode = document.getElementById('optimizedCode').textContent;
    navigator.clipboard.writeText(optimizedCode).then(() => {
        const btn = document.getElementById('copyOptimizedBtn');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        btn.style.background = '#10b981';
        btn.style.color = 'white';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.background = '';
            btn.style.color = '';
        }, 2000);
    });
}

function handleExport() {
    const results = {
        timestamp: new Date().toISOString(),
        language: document.getElementById('detectedLang').textContent,
        qualityScore: document.getElementById('qualityScore').textContent,
        issues: currentIssues,
        optimizedCode: document.getElementById('optimizedCode').textContent,
        explanation: document.getElementById('explanation').textContent
    };
    
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `code-analysis-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function showLoading() {
    document.getElementById('loadingSection').classList.remove('hidden');
    animateLoadingSteps();
}

function hideLoading() {
    document.getElementById('loadingSection').classList.add('hidden');
}

function animateLoadingSteps() {
    const steps = document.querySelectorAll('.step');
    let currentStep = 0;
    
    const interval = setInterval(() => {
        if (currentStep > 0) {
            steps[currentStep - 1].classList.remove('active');
            steps[currentStep - 1].querySelector('i').className = 'fas fa-check';
        }
        
        if (currentStep < steps.length) {
            steps[currentStep].classList.add('active');
            currentStep++;
        } else {
            clearInterval(interval);
        }
    }, 800);
}

function showResults() {
    document.getElementById('resultsSection').classList.remove('hidden');
}

function hideResults() {
    document.getElementById('resultsSection').classList.add('hidden');
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
    
    errorSection.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });
}

function hideError() {
    document.getElementById('errorSection').classList.add('hidden');
}

function disableButton(disabled) {
    const btn = document.getElementById('analyzeBtn');
    btn.disabled = disabled;
    if (disabled) {
        btn.querySelector('span').textContent = 'Analyzing...';
    } else {
        btn.querySelector('span').textContent = 'Analyze Code';
    }
}
