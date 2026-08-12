from typing import List, Optional
from pydantic import BaseModel, Field

class MCQOption(BaseModel):
    id: str = Field(..., description="Unique identifier for the option, e.g., 'A', 'B', 'C', 'D'")
    text: str = Field(..., description="The text of the option")

class GeneratedQuestionSchema(BaseModel):
    """
    The structured schema requested from the AI Provider.
    """
    question_text: str = Field(..., description="The actual question text")
    options: Optional[List[MCQOption]] = Field(None, description="Provide 4 options if the question is an MCQ, otherwise null")
    correct_answer: str = Field(..., description="The correct answer text (or option ID if MCQ)")
    explanation: str = Field(..., description="Detailed explanation of why the answer is correct, citing the provided knowledge context")
    source_citations: List[str] = Field(..., description="Identify the specific sources (e.g., 'Source 1', 'Source 2') that support this question")

class GeneratedQuestionListSchema(BaseModel):
    """
    Schema for generating a batch of questions.
    """
    questions: List[GeneratedQuestionSchema] = Field(..., description="The list of generated questions for this batch.")

def validate_question_logic(data: GeneratedQuestionSchema, expected_type: str) -> str:
    """
    Validates logical constraints that Pydantic schemas can't easily catch.
    Returns an error string if invalid, or empty string if valid.
    """
    expected_type = expected_type.upper()
    
    if not data.question_text.strip():
        return "Question text is empty."
        
    if not data.explanation.strip():
        return "Explanation is missing."

    if expected_type == "MCQ":
        if not data.options or len(data.options) < 2:
            return "MCQ requires at least 2 options."
            
        # Ensure correct_answer matches one of the options' id or text
        valid_answer = False
        for opt in data.options:
            if data.correct_answer.strip().lower() in [opt.id.strip().lower(), opt.text.strip().lower()]:
                valid_answer = True
                break
                
        if not valid_answer:
            return f"Correct answer '{data.correct_answer}' does not match any provided options."
            
    else:
        if not data.correct_answer.strip():
            return "Correct answer is missing."
            
    return ""
