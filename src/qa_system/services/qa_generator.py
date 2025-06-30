"""
QA Generation service using LangChain and Google Gemini
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json

logger = logging.getLogger(__name__)


class QuestionType(str, Enum):
    """Type of question"""
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    ESSAY = "essay"
    SHORT_ANSWER = "short_answer"


class DifficultyLevel(str, Enum):
    """Difficulty level"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GeneratedQuestion(BaseModel):
    """Generated question"""
    question: str = Field(description="Question text")
    question_type: QuestionType = Field(description="Type of question")
    difficulty: DifficultyLevel = Field(description="Difficulty level")
    choices: Optional[List[str]] = Field(default=None, description="Choices (for multiple choice questions)")
    correct_answer: str = Field(description="Correct answer")
    explanation: str = Field(description="Explanation")
    keywords: List[str] = Field(description="Related keywords")


class QASet(BaseModel):
    """Set of questions for a slide"""
    slide_number: int = Field(description="Slide number")
    slide_title: str = Field(description="Slide title")
    questions: List[GeneratedQuestion] = Field(description="List of generated questions")


class QAGenerator:
    """QA generation service"""
    
    def __init__(self, google_api_key: str, model_name: str = "gemini-1.5-flash"):
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=google_api_key,
            model=model_name,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        self.parser = PydanticOutputParser(pydantic_object=GeneratedQuestion)
    
    def generate_questions_for_slide(
        self, 
        slide_content: Dict[str, Any], 
        num_questions: int = 2,
        difficulty_distribution: Dict[DifficultyLevel, int] = None
    ) -> QASet:
        """Generate questions from the content of a single slide"""
        
        if difficulty_distribution is None:
            difficulty_distribution = {
                DifficultyLevel.EASY: 1,
                DifficultyLevel.MEDIUM: 1,
                DifficultyLevel.HARD: 0
            }
        
        questions = []
        
        for difficulty, count in difficulty_distribution.items():
            for _ in range(count):
                question = self._generate_single_question(slide_content, difficulty)
                if question:
                    questions.append(question)
        
        return QASet(
            slide_number=slide_content["slide_number"],
            slide_title=slide_content["title"],
            questions=questions
        )
    
    def generate_questions_for_multiple_slides(
        self,
        slides_content: List[Dict[str, Any]],
        questions_per_slide: int = 2
    ) -> List[QASet]:
        """Generate questions from the content of multiple slides"""
        
        qa_sets = []
        
        for slide_content in slides_content:
            # Only generate questions if the slide has sufficient content
            if self._has_sufficient_content(slide_content):
                qa_set = self.generate_questions_for_slide(
                    slide_content, 
                    num_questions=questions_per_slide
                )
                qa_sets.append(qa_set)
                logger.info(f"Questions generated for slide {slide_content['slide_number']}")
            else:
                logger.warning(f"Slide {slide_content['slide_number']} skipped due to insufficient content")
        
        return qa_sets
    
    def _generate_single_question(
        self, 
        slide_content: Dict[str, Any], 
        difficulty: DifficultyLevel
    ) -> Optional[GeneratedQuestion]:
        """Generate a single question"""
        
        try:
            prompt = self._create_question_prompt(slide_content, difficulty)
            
            response = self.llm.invoke(prompt)
            
            # Parse JSON response
            question_data = self._parse_response(response.content)
            
            if question_data:
                return GeneratedQuestion(**question_data)
            
        except Exception as e:
            logger.error(f"Error occurred during question generation: {e}")
            return None
    
    def _create_question_prompt(
        self, 
        slide_content: Dict[str, Any], 
        difficulty: DifficultyLevel
    ) -> List[BaseMessage]:
        """Create a prompt for question generation"""
        
        difficulty_instructions = {
            DifficultyLevel.EASY: "Simple question to check understanding of basic terms and concepts",
            DifficultyLevel.MEDIUM: "Moderate question asking about application or relationships of concepts", 
            DifficultyLevel.HARD: "Difficult question requiring deep understanding or critical thinking"
        }
        
        system_message = f"""
You are an expert question creator for educational content. Please generate one question to assess student understanding from the provided slide content.

## Instructions:
1. Difficulty: {difficulty_instructions[difficulty]}
2. Question type: one of multiple_choice (4 options), single_choice (2 options), essay, or short_answer
3. Create a specific and clear question based on the content
4. For multiple choice, include plausible distractors
5. Provide the correct answer and a detailed explanation

## Important:
Respond only in valid JSON format as shown below. Do not include any explanations, only valid JSON in the following format.

JSON format:
- question: Question text
- question_type: Type of question (multiple_choice, single_choice, essay, short_answer)
- difficulty: {difficulty.value}
- choices: Array of choices (for multiple choice only) or null
- correct_answer: Correct answer
- explanation: Detailed explanation
- keywords: Array of related keywords

Note: For non-choice questions, set choices to null.
"""
        
        user_message = f"""
## Slide Information:
- Slide number: {slide_content['slide_number']}
- Title: {slide_content['title']}
- Content: {slide_content['content']}
- Bullet points: {', '.join(slide_content['bullet_points'])}
- Full text: {slide_content['full_text']}

Please generate one question from the above content.
"""
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", user_message)
        ])
        
        return prompt_template.format_messages()
    
    def _parse_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM response"""
        try:
            # Extract JSON using multiple patterns
            json_content = self._extract_json_from_response(response_content)
            
            if not json_content:
                logger.error(f"JSON content not found. Response: {response_content[:200]}...")
                return None
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Validate required fields
            required_fields = ["question", "question_type", "difficulty", "correct_answer", "explanation"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Required field '{field}' not found")
                    return None
            
            # Set default value
            if "keywords" not in data:
                data["keywords"] = []
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Response content: {response_content[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def _extract_json_from_response(self, response_content: str) -> Optional[str]:
        """Extract the JSON part from the response"""
        # Pattern 1: ```json...``` block
        if "```json" in response_content:
            start = response_content.find("```json") + 7
            end = response_content.find("```", start)
            if end != -1:
                return response_content[start:end].strip()
        
        # Pattern 2: ```...``` block (no json specified)
        if "```" in response_content:
            start = response_content.find("```") + 3
            end = response_content.find("```", start)
            if end != -1:
                potential_json = response_content[start:end].strip()
                # Check if it's JSON
                if potential_json.startswith("{") and potential_json.endswith("}"):
                    return potential_json
        
        # Pattern 3: Directly extract { ... } block
        start_brace = response_content.find("{")
        if start_brace != -1:
            # Find the matching closing brace
            brace_count = 0
            for i, char in enumerate(response_content[start_brace:], start_brace):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return response_content[start_brace:i+1]
        
        # Pattern 4: Try the whole content
        content = response_content.strip()
        if content.startswith("{") and content.endswith("}"):
            return content
        
        return None
    
    def _has_sufficient_content(self, slide_content: Dict[str, Any]) -> bool:
        """Check if the slide has sufficient content"""
        full_text = slide_content.get("full_text", "")
        content = slide_content.get("content", "")
        bullet_points = slide_content.get("bullet_points", [])
        
        # Check minimum text length and content elements
        min_text_length = 50
        has_meaningful_content = (
            len(full_text) >= min_text_length or
            len(content) >= min_text_length or
            len(bullet_points) >= 2
        )
        
        return has_meaningful_content
    
    def generate_comprehensive_qa(
        self, 
        slides_content: List[Dict[str, Any]],
        total_questions: int = 20,
        difficulty_ratio: Dict[str, float] = None
    ) -> List[QASet]:
        """Generate a comprehensive QA set"""
        
        if difficulty_ratio is None:
            difficulty_ratio = {"easy": 0.4, "medium": 0.4, "hard": 0.2}
        
        # Calculate the number of questions for each difficulty
        easy_count = int(total_questions * difficulty_ratio["easy"])
        medium_count = int(total_questions * difficulty_ratio["medium"]) 
        hard_count = total_questions - easy_count - medium_count
        
        # Calculate question allocation per slide
        valid_slides = [s for s in slides_content if self._has_sufficient_content(s)]
        
        if not valid_slides:
            logger.warning("No slides suitable for question generation")
            return []
        
        questions_per_slide = total_questions // len(valid_slides)
        remaining_questions = total_questions % len(valid_slides)
        
        qa_sets = []
        difficulty_counts = {
            DifficultyLevel.EASY: easy_count,
            DifficultyLevel.MEDIUM: medium_count,
            DifficultyLevel.HARD: hard_count
        }
        
        for i, slide_content in enumerate(valid_slides):
            # Determine the number of questions for this slide
            slide_questions = questions_per_slide
            if i < remaining_questions:
                slide_questions += 1
            
            # Determine difficulty distribution
            slide_difficulty_dist = self._distribute_difficulty_for_slide(
                slide_questions, difficulty_counts
            )
            
            qa_set = self.generate_questions_for_slide(
                slide_content,
                num_questions=slide_questions,
                difficulty_distribution=slide_difficulty_dist
            )
            
            qa_sets.append(qa_set)
        
        return qa_sets
    
    def _distribute_difficulty_for_slide(
        self, 
        questions_count: int, 
        remaining_difficulty_counts: Dict[DifficultyLevel, int]
    ) -> Dict[DifficultyLevel, int]:
        """Determine difficulty distribution for each slide"""
        
        distribution = {
            DifficultyLevel.EASY: 0,
            DifficultyLevel.MEDIUM: 0,
            DifficultyLevel.HARD: 0
        }
        
        # Allocate based on remaining questions
        for difficulty in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]:
            available = remaining_difficulty_counts[difficulty]
            if available > 0 and questions_count > 0:
                allocated = min(1, available, questions_count)
                distribution[difficulty] = allocated
                remaining_difficulty_counts[difficulty] -= allocated
                questions_count -= allocated
        
        return distribution