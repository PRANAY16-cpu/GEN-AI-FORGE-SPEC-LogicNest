from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import google.generativeai as genai
from transformers import pipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeRefine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set. Using fallback mode.")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')

try:
    hf_sentiment = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    logger.info("Hugging Face model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Hugging Face model: {e}")
    hf_sentiment = None


class CodeRequest(BaseModel):
    code: str


class CodeResponse(BaseModel):
    detected_language: str
    quality_score: int
    issues: list
    optimized_code: str
    explanation: str


def detect_language(code):
    code_lower = code.lower()
    
    patterns = {
        'python': [r'def\s+\w+', r'import\s+\w+', r'print\s*\(', r'if\s+__name__\s*==', r'class\s+\w+'],
        'javascript': [r'function\s+\w+', r'const\s+\w+', r'let\s+\w+', r'var\s+\w+', r'=>', r'console\.log'],
        'java': [r'public\s+class', r'public\s+static\s+void\s+main', r'System\.out\.println', r'private\s+\w+'],
        'c++': [r'#include\s*<', r'std::', r'cout\s*<<', r'int\s+main\s*\(', r'namespace\s+\w+'],
        'c': [r'#include\s*<', r'printf\s*\(', r'int\s+main\s*\(', r'scanf\s*\('],
        'ruby': [r'def\s+\w+', r'puts\s+', r'require\s+', r'end\s*$', r'class\s+\w+'],
        'go': [r'func\s+\w+', r'package\s+\w+', r'fmt\.Print', r'import\s+\('],
        'rust': [r'fn\s+\w+', r'let\s+mut', r'println!', r'use\s+\w+'],
        'php': [r'<\?php', r'\$\w+', r'echo\s+', r'function\s+\w+'],
        'swift': [r'func\s+\w+', r'var\s+\w+', r'let\s+\w+', r'print\s*\(', r'import\s+\w+'],
        'kotlin': [r'fun\s+\w+', r'val\s+\w+', r'var\s+\w+', r'println\s*\('],
        'typescript': [r'interface\s+\w+', r'type\s+\w+', r':\s*\w+', r'function\s+\w+'],
        'sql': [r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'INSERT\s+INTO', r'UPDATE\s+'],
        'html': [r'<html', r'<div', r'<body', r'<!DOCTYPE'],
        'css': [r'\.\w+\s*{', r'#\w+\s*{', r':\s*\w+;', r'@media'],
    }
    
    scores = {}
    for lang, pattern_list in patterns.items():
        score = 0
        for pattern in pattern_list:
            if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                score += 1
        scores[lang] = score
    
    if max(scores.values()) == 0:
        return "unknown"
    
    return max(scores, key=scores.get)


def analyze_code_quality(code, language):
    issues = []
    quality_score = 100
    
    lines = code.split('\n')
    line_count = len([l for l in lines if l.strip()])
    
    if line_count > 100:
        issues.append("Code is quite long. Consider breaking it into smaller functions.")
        quality_score -= 10
    
    if language == 'python':
        if not re.search(r'def\s+\w+', code):
            issues.append("No functions defined. Consider using functions for better code organization.")
            quality_score -= 15
        
        if 'import' not in code.lower() and line_count > 10:
            issues.append("No imports found. You might be missing useful libraries.")
            quality_score -= 5
        
        single_letter_vars = re.findall(r'\b[a-z]\s*=', code)
        if len(single_letter_vars) > 3:
            issues.append("Too many single-letter variable names. Use descriptive names.")
            quality_score -= 10
    
    elif language == 'javascript':
        if 'var ' in code:
            issues.append("Using 'var' instead of 'let' or 'const'. Use modern declarations.")
            quality_score -= 10
        
        if not re.search(r'function\s+\w+|const\s+\w+\s*=\s*\(.*\)\s*=>', code):
            issues.append("No functions defined. Consider using functions for better code organization.")
            quality_score -= 15
    
    comment_lines = len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')])
    if line_count > 20 and comment_lines < 3:
        issues.append("Limited comments. Add comments to explain complex logic.")
        quality_score -= 10
    
    if '\t' in code:
        issues.append("Mixed tabs and spaces detected. Use consistent indentation.")
        quality_score -= 5
    
    long_lines = [l for l in lines if len(l) > 120]
    if long_lines:
        issues.append(f"Found {len(long_lines)} lines longer than 120 characters. Break them up for readability.")
        quality_score -= 5
    
    if hf_sentiment and len(code) < 500:
        try:
            code_sample = code[:500]
            sentiment_result = hf_sentiment(code_sample)[0]
            if sentiment_result['label'] == 'NEGATIVE' and sentiment_result['score'] > 0.8:
                quality_score -= 5
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
    
    return max(quality_score, 0), issues


def optimize_code_with_gemini(code, language, issues):
    if not GEMINI_API_KEY:
        optimized = code
        explanation = "API key not configured. Showing original code with basic recommendations:\n\n"
        explanation += "Consider the following improvements:\n"
        for issue in issues:
            explanation += f"- {issue}\n"
        explanation += "\nFor full AI-powered optimization, please configure GEMINI_API_KEY."
        return optimized, explanation
    
    try:
        prompt = f"""You are an expert code reviewer and optimizer. 

Language: {language}

Original Code:
```
{code}
```

Issues Found:
{chr(10).join(f'- {issue}' for issue in issues)}

Please provide:
1. An optimized version of the code that addresses the issues
2. A beginner-friendly explanation of what you changed and why

Format your response EXACTLY as:
OPTIMIZED_CODE:
```
[optimized code here]
```

EXPLANATION:
[beginner-friendly explanation here]
"""
        
        response = gemini_model.generate_content(prompt)
        response_text = response.text
        
        optimized_match = re.search(r'OPTIMIZED_CODE:\s*```(?:\w+)?\s*(.*?)\s*```', response_text, re.DOTALL)
        explanation_match = re.search(r'EXPLANATION:\s*(.*)', response_text, re.DOTALL)
        
        if optimized_match:
            optimized_code = optimized_match.group(1).strip()
        else:
            optimized_code = code
        
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        else:
            explanation = "The code has been analyzed. Please review the optimized version."
        
        return optimized_code, explanation
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        optimized = code
        explanation = f"Unable to generate AI optimization due to: {str(e)}\n\n"
        explanation += "Basic recommendations based on static analysis:\n"
        for issue in issues:
            explanation += f"- {issue}\n"
        return optimized, explanation


@app.get("/")
def read_root():
    return {"message": "CodeRefine API is running", "status": "healthy"}


@app.post("/review", response_model=CodeResponse)
async def review_code(request: CodeRequest):
    try:
        code = request.code.strip()
        
        if not code:
            raise HTTPException(status_code=400, detail="Code cannot be empty")
        
        if len(code) > 50000:
            raise HTTPException(status_code=400, detail="Code is too long (max 50000 characters)")
        
        detected_language = detect_language(code)
        
        quality_score, issues = analyze_code_quality(code, detected_language)
        
        optimized_code, explanation = optimize_code_with_gemini(code, detected_language, issues)
        
        return CodeResponse(
            detected_language=detected_language.capitalize(),
            quality_score=quality_score,
            issues=issues,
            optimized_code=optimized_code,
            explanation=explanation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing code review: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

# requirements.txt
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
google-generativeai==0.3.1
transformers==4.35.2
torch==2.1.1