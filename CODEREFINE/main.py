from urllib import response
from click import prompt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import re
#import google.generativeai as genai
from google import genai
#from transform
from transformers import pipeline


#from typer import prompters
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CodeRefine API",
    description="AI-Powered Code Review and Optimization Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCO-mxrv4nEq6QdL274bTZh3qkc4XgQJo0")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set. Using fallback mode.")
    gemini_model = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)
gemini_model = "gemini-1.5-turbo"  # Just store the model name

    




hf_sentiment = None  # Disable Hugging Face for demo
logger.info("Hugging Face pipeline disabled for demo")



class Issue(BaseModel):
    title: str
    description: str
    severity: str
    location: Optional[str] = None


class CodeRequest(BaseModel):
    code: str
    language: Optional[str] = "auto"
    depth: Optional[str] = "standard"
    check_security: Optional[bool] = True
    check_performance: Optional[bool] = True
    check_best_practices: Optional[bool] = True


class CodeResponse(BaseModel):
    detected_language: str
    quality_score: int
    security_score: int
    performance_score: int
    maintainability_score: int
    line_count: int
    complexity: str
    issues: List[Issue]
    optimized_code: str
    explanation: str
    complexity_reduction: str


LANGUAGE_PATTERNS = {
    'python': [
        r'def\s+\w+\s*\(',
        r'import\s+\w+',
        r'from\s+\w+\s+import',
        r'print\s*\(',
        r'if\s+__name__\s*==\s*["\']__main__["\']',
        r'class\s+\w+\s*:',
        r':\s*$'
    ],
    'javascript': [
        r'function\s+\w+\s*\(',
        r'const\s+\w+\s*=',
        r'let\s+\w+\s*=',
        r'var\s+\w+\s*=',
        r'=>',
        r'console\.log',
        r'document\.',
        r'window\.'
    ],
    'typescript': [
        r'interface\s+\w+',
        r'type\s+\w+\s*=',
        r':\s*\w+\s*[;,\)]',
        r'function\s+\w+\s*\(',
        r'class\s+\w+',
        r'export\s+(default\s+)?(class|function|interface)'
    ],
    'java': [
        r'public\s+class',
        r'public\s+static\s+void\s+main',
        r'System\.out\.println',
        r'private\s+\w+\s+\w+',
        r'@\w+',
        r'package\s+\w+'
    ],
    'cpp': [
        r'#include\s*<',
        r'std::',
        r'cout\s*<<',
        r'int\s+main\s*\(',
        r'namespace\s+\w+',
        r'using\s+namespace'
    ],
    'c': [
        r'#include\s*<',
        r'printf\s*\(',
        r'int\s+main\s*\(',
        r'scanf\s*\(',
        r'malloc\s*\('
    ],
    'csharp': [
        r'using\s+System',
        r'namespace\s+\w+',
        r'class\s+\w+',
        r'public\s+static\s+void\s+Main',
        r'Console\.WriteLine'
    ],
    'go': [
        r'func\s+\w+\s*\(',
        r'package\s+\w+',
        r'fmt\.Print',
        r'import\s+\(',
        r':=',
        r'go\s+\w+'
    ],
    'rust': [
        r'fn\s+\w+\s*\(',
        r'let\s+mut',
        r'println!',
        r'use\s+\w+',
        r'impl\s+\w+',
        r'struct\s+\w+'
    ],
    'php': [
        r'<\?php',
        r'\$\w+',
        r'echo\s+',
        r'function\s+\w+\s*\(',
        r'->'
    ],
    'ruby': [
        r'def\s+\w+',
        r'puts\s+',
        r'require\s+',
        r'end\s*$',
        r'class\s+\w+',
        r'@\w+'
    ],
    'swift': [
        r'func\s+\w+\s*\(',
        r'var\s+\w+',
        r'let\s+\w+',
        r'print\s*\(',
        r'import\s+\w+',
        r'class\s+\w+'
    ],
    'kotlin': [
        r'fun\s+\w+\s*\(',
        r'val\s+\w+',
        r'var\s+\w+',
        r'println\s*\(',
        r'class\s+\w+',
        r'object\s+\w+'
    ]
}


def detect_language(code: str) -> str:
    """Detect programming language from code"""
    code_lower = code.lower()
    scores = {}
    
    for lang, patterns in LANGUAGE_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, code, re.IGNORECASE | re.MULTILINE)
            score += len(matches)
        scores[lang] = score
    
    if max(scores.values()) == 0:
        return "unknown"
    
    detected = max(scores, key=scores.get)
    return detected


def calculate_complexity(code: str) -> str:
    """Calculate code complexity"""
    lines = [l for l in code.split('\n') if l.strip()]
    line_count = len(lines)
    
    nesting_level = 0
    max_nesting = 0
    for line in lines:
        stripped = line.strip()
        if any(kw in stripped for kw in ['if', 'for', 'while', 'def', 'class', 'function']):
            nesting_level += 1
            max_nesting = max(max_nesting, nesting_level)
        if stripped in ['}', 'end']:
            nesting_level = max(0, nesting_level - 1)
    
    if line_count > 200 or max_nesting > 5:
        return "High"
    elif line_count > 100 or max_nesting > 3:
        return "Medium"
    else:
        return "Low"


def analyze_code_quality(code: str, language: str, check_security: bool, 
                        check_performance: bool, check_best_practices: bool) -> tuple:
    """Analyze code and return quality metrics and issues"""
    issues = []
    quality_score = 100
    security_score = 100
    performance_score = 100
    maintainability_score = 100
    
    lines = code.split('\n')
    line_count = len([l for l in lines if l.strip()])
    
    if check_best_practices:
        if line_count > 100:
            issues.append(Issue(
                title="Long Code Block",
                description="Code is quite long. Consider breaking it into smaller, more manageable functions or modules.",
                severity="warning",
                location=None
            ))
            quality_score -= 10
            maintainability_score -= 15
        
        comment_lines = len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')])
        if line_count > 20 and comment_lines < 3:
            issues.append(Issue(
                title="Insufficient Comments",
                description="Limited comments found. Add comments to explain complex logic and improve code readability.",
                severity="info",
                location=None
            ))
            quality_score -= 5
            maintainability_score -= 10
    
    if language == 'python' and check_best_practices:
        if not re.search(r'def\s+\w+', code):
            issues.append(Issue(
                title="No Functions Defined",
                description="No functions defined. Consider using functions for better code organization and reusability.",
                severity="warning",
                location=None
            ))
            quality_score -= 15
            maintainability_score -= 20
        
        single_letter_vars = re.findall(r'\b[a-z]\s*=', code)
        if len(single_letter_vars) > 3:
            issues.append(Issue(
                title="Poor Variable Naming",
                description="Too many single-letter variable names detected. Use descriptive names for better code readability.",
                severity="warning",
                location=None
            ))
            quality_score -= 10
            maintainability_score -= 15
        
        if check_security:
            if 'eval(' in code or 'exec(' in code:
                issues.append(Issue(
                    title="Dangerous Function Usage",
                    description="Usage of eval() or exec() detected. These functions can execute arbitrary code and pose security risks.",
                    severity="critical",
                    location=None
                ))
                quality_score -= 20
                security_score -= 30
    
    elif language == 'javascript' and check_best_practices:
        if 'var ' in code:
            issues.append(Issue(
                title="Deprecated Variable Declaration",
                description="Using 'var' instead of 'let' or 'const'. Use modern ES6+ declarations for better scoping.",
                severity="warning",
                location=None
            ))
            quality_score -= 10
        
        if check_security:
            if 'eval(' in code:
                issues.append(Issue(
                    title="Security Risk: eval()",
                    description="eval() function detected. This can execute arbitrary code and is a security vulnerability.",
                    severity="critical",
                    location=None
                ))
                quality_score -= 20
                security_score -= 30
            
            if 'innerHTML' in code and '=' in code:
                issues.append(Issue(
                    title="XSS Vulnerability Risk",
                    description="Direct innerHTML assignment detected. This may lead to XSS vulnerabilities. Consider using textContent or sanitization.",
                    severity="critical",
                    location=None
                ))
                security_score -= 25
    
    if check_performance:
        long_lines = [i+1 for i, l in enumerate(lines) if len(l) > 120]
        if long_lines:
            issues.append(Issue(
                title="Long Lines Detected",
                description=f"Found {len(long_lines)} lines longer than 120 characters. Break them up for better readability.",
                severity="info",
                location=f"{long_lines[0]}" if long_lines else None
            ))
            quality_score -= 5
        
        if '\t' in code:
            issues.append(Issue(
                title="Inconsistent Indentation",
                description="Mixed tabs and spaces detected. Use consistent indentation (preferably spaces).",
                severity="warning",
                location=None
            ))
            quality_score -= 5
            maintainability_score -= 10
    
    if check_security and language in ['python', 'javascript', 'php']:
        if re.search(r'password\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            issues.append(Issue(
                title="Hardcoded Credentials",
                description="Hardcoded password detected in code. Store credentials in environment variables or secure vaults.",
                severity="critical",
                location=None
            ))
            security_score -= 40
            quality_score -= 20
    
    quality_score = max(quality_score, 0)
    security_score = max(security_score, 0)
    performance_score = max(performance_score, 0)
    maintainability_score = max(maintainability_score, 0)
    
    return quality_score, security_score, performance_score, maintainability_score, issues


def optimize_code_with_gemini(code: str, language: str, issues: List[Issue], depth: str) -> tuple:
    # Temporary dummy function for demo
    optimized_code = code
    explanation = "AI optimization is disabled for the demo."
    complexity_reduction = "0%"
    return optimized_code, explanation, complexity_reduction

    try:
        issues_text = "\n".join([f"- [{i.severity.upper()}] {i.title}: {i.description}" for i in issues])
        
        depth_instructions = {
            "quick": "Provide a quick optimization focusing on the most critical issues.",
            "standard": "Provide standard optimizations covering major issues and improvements.",
            "deep": "Provide deep analysis with comprehensive optimizations, refactoring suggestions, and performance improvements."
        }
        
        prompt = f"""You are an expert code reviewer and optimizer specializing in {language}.

Analysis Depth: {depth}
{depth_instructions.get(depth, depth_instructions['standard'])}

Original Code:
```{language}
{code}
```

Issues Detected:
{issues_text}

Please provide:
1. An optimized version of the code that addresses all issues
2. A beginner-friendly explanation of changes
3. Performance improvements and best practices applied

Format your response EXACTLY as follows:

OPTIMIZED_CODE:
```{language}
[your optimized code here]
```

EXPLANATION:
## Summary
[Brief overview of changes]

## Key Improvements
- [Improvement 1]
- [Improvement 2]
- [Improvement 3]

## Security Enhancements
[Security improvements if applicable]

## Performance Optimizations
[Performance improvements if applicable]

## Best Practices Applied
[Best practices implemented]

## Learning Points
[Educational insights for beginners]
"""
        
        response = client.generate_text(
           model=gemini_model,
            prompt=prompt,
            temperature=0.2
          )
        response_text = response.output_text

        
        optimized_match = re.search(r'OPTIMIZED_CODE:\s*```(?:\w+)?\s*(.*?)\s*```', response_text, re.DOTALL)
        explanation_match = re.search(r'EXPLANATION:\s*(.*)', response_text, re.DOTALL)
        
        if optimized_match:
            optimized_code = optimized_match.group(1).strip()
        else:
            optimized_code = code
        
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        else:
            explanation = "Code has been analyzed. Please review the optimized version."
        
        original_lines = len(code.split('\n'))
        optimized_lines = len(optimized_code.split('\n'))
        reduction = max(0, ((original_lines - optimized_lines) / original_lines) * 100) if original_lines > 0 else 0
        complexity_reduction = f"{reduction:.1f}%"
        
        return optimized_code, explanation, complexity_reduction
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        optimized = code
        explanation = f"## Optimization Error\n\nUnable to generate AI optimization: {str(e)}\n\n"
        explanation += "**Recommendations based on static analysis:**\n"
        for issue in issues:
            explanation += f"- **{issue.title}**: {issue.description}\n"
        return optimized, explanation, "0%"


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "message": "CodeRefine API is running",
        "status": "healthy",
        "version": "1.0.0",
        "ai_enabled": bool(GEMINI_API_KEY)
    }


@app.post("/review", response_model=CodeResponse)
async def review_code(request: CodeRequest):
    """Main code review endpoint"""
    try:
        code = request.code.strip()
        
        if not code:
            raise HTTPException(status_code=400, detail="Code cannot be empty")
        
        if len(code) > 100000:
            raise HTTPException(status_code=400, detail="Code is too long (max 100000 characters)")
        
        if request.language == "auto":
            detected_language = detect_language(code)
        else:
            detected_language = request.language
        
        line_count = len([l for l in code.split('\n') if l.strip()])
        complexity = calculate_complexity(code)
        
        quality_score, security_score, performance_score, maintainability_score, issues = analyze_code_quality(
            code, 
            detected_language,
            request.check_security,
            request.check_performance,
            request.check_best_practices
        )
        
        optimized_code, explanation, complexity_reduction = optimize_code_with_gemini(
            code, 
            detected_language, 
            issues,
            request.depth
        )
        
        return CodeResponse(
            detected_language=detected_language.capitalize(),
            quality_score=quality_score,
            security_score=security_score,
            performance_score=performance_score,
            maintainability_score=maintainability_score,
            line_count=line_count,
            complexity=complexity,
            issues=issues,
            optimized_code=optimized_code,
            explanation=explanation,
            complexity_reduction=complexity_reduction
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing code review: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

'''# requirements.txt
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
google-generativeai==0.3.1
transformers==4.35.2
torch==2.1.1'''
