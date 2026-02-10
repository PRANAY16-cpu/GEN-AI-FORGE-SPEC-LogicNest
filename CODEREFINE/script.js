const API_URL = 'http://localhost:8000';

document.getElementById('reviewBtn').addEventListener('click', async () => {
    const codeInput = document.getElementById('codeInput').value.trim();
    
    if (!codeInput) {
        showError('Please enter some code to review!');
        return;
    }
    
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
            body: JSON.stringify({ code: codeInput })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to analyze code');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(`Error: ${error.message}`);
    } finally {
        hideLoading();
        disableButton(false);
    }
});

document.getElementById('copyBtn').addEventListener('click', () => {
    const optimizedCode = document.getElementById('optimizedCode').textContent;
    navigator.clipboard.writeText(optimizedCode).then(() => {
        const copyBtn = document.getElementById('copyBtn');
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✅ Copied!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    });
});

function displayResults(data) {
    document.getElementById('detectedLang').textContent = data.detected_language;
    document.getElementById('qualityScore').textContent = data.quality_score;
    
    const scoreCircle = document.querySelector('.score-circle');
    const score = data.quality_score;
    if (score >= 80) {
        scoreCircle.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
    } else if (score >= 60) {
        scoreCircle.style.background = 'linear-gradient(135deg, #ffc107 0%, #ff9800 100%)';
    } else {
        scoreCircle.style.background = 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)';
    }
    
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';
    if (data.issues && data.issues.length > 0) {
        data.issues.forEach(issue => {
            const li = document.createElement('li');
            li.textContent = issue;
            issuesList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'No major issues found!';
        li.style.borderLeftColor = '#28a745';
        li.style.color = '#28a745';
        issuesList.appendChild(li);
    }
    
    document.getElementById('optimizedCode').textContent = data.optimized_code;
    
    const explanationDiv = document.getElementById('explanation');
    explanationDiv.innerHTML = formatExplanation(data.explanation);
    
    showResults();
}

function formatExplanation(explanation) {
    const paragraphs = explanation.split('\n\n');
    return paragraphs.map(p => {
        p = p.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        p = p.replace(/\n/g, '<br>');
        return `<p>${p}</p>`;
    }).join('');
}

function showLoading() {
    document.getElementById('loadingSection').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingSection').classList.add('hidden');
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
}

function hideError() {
    document.getElementById('errorSection').classList.add('hidden');
}

function disableButton(disabled) {
    document.getElementById('reviewBtn').disabled = disabled;
}