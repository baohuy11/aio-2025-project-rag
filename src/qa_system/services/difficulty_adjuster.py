"""
Difficulty adjustment service for QA generation
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class DifficultyLevel(str, Enum):
    """Difficulty level"""
    EASY = "easy"
    MEDIUM = "medium" 
    HARD = "hard"


@dataclass
class DifficultyParameters:
    """Difficulty adjustment parameters"""
    cognitive_level: str  # Cognitive level (remember, understand, apply, analyze, evaluate, create)
    question_complexity: str  # Complexity of the question
    content_depth: str  # Depth of content
    thinking_time: str  # Estimated thinking time
    vocabulary_level: str  # Vocabulary level
    concept_integration: str  # Need for concept integration


class DifficultyAdjuster:
    """Difficulty adjustment service"""
    
    def __init__(self):
        self.difficulty_parameters = self._initialize_difficulty_parameters()
    
    def _initialize_difficulty_parameters(self) -> Dict[DifficultyLevel, DifficultyParameters]:
        """Initialize difficulty parameters"""
        return {
            DifficultyLevel.EASY: DifficultyParameters(
                cognitive_level="Remember/Understand",
                question_complexity="Simple fact check",
                content_depth="Surface-level content",
                thinking_time="Within 30 seconds",
                vocabulary_level="Basic technical terms",
                concept_integration="Single concept"
            ),
            DifficultyLevel.MEDIUM: DifficultyParameters(
                cognitive_level="Apply/Analyze",
                question_complexity="Relating concepts",
                content_depth="Moderate understanding",
                thinking_time="1-2 minutes",
                vocabulary_level="Standard technical terms",
                concept_integration="Relation of multiple concepts"
            ),
            DifficultyLevel.HARD: DifficultyParameters(
                cognitive_level="Evaluate/Create",
                question_complexity="Critical thinking",
                content_depth="Deep understanding and application",
                thinking_time="Over 3 minutes",
                vocabulary_level="Advanced technical terms",
                concept_integration="Complex concept integration"
            )
        }
    
    def get_prompt_instructions(self, difficulty: DifficultyLevel) -> str:
        """Generate prompt instructions according to difficulty"""
        params = self.difficulty_parameters[difficulty]
        
        instructions = {
            DifficultyLevel.EASY: f"""
## Difficulty: Easy
**Cognitive level**: {params.cognitive_level}
**Question features**: 
- Check facts or definitions directly explained in the lecture
- Ask about the meaning of simple terms or basic concepts
- Can be answered by memorization or simple understanding
- Focus on a single concept

**Instructions**:
- Ask from content clearly stated in the lecture material
- Use only basic technical terms
- Make choices clearly distinguishable
- Should be answerable within {params.thinking_time}
""",
            
            DifficultyLevel.MEDIUM: f"""
## Difficulty: Medium
**Cognitive level**: {params.cognitive_level}
**Question features**:
- Ask about understanding and simple application of concepts
- Requires understanding relationships between multiple concepts
- Make students think of concrete examples or application situations
- Requires inference or judgment

**Instructions**:
- Apply lecture concepts to real situations
- Require thinking by relating multiple concepts
- Include plausible distractors
- Should require about {params.thinking_time} of thinking time
""",
            
            DifficultyLevel.HARD: f"""
## Difficulty: Hard
**Cognitive level**: {params.cognitive_level}
**Question features**:
- Require deep understanding and critical thinking
- Integrate multiple concepts to derive new conclusions
- Require problem-solving or creative thinking
- Require broad application and abstract thinking

**Instructions**:
- Analyze or evaluate new situations based on lecture content
- Require understanding of complex concept interrelations
- Reasoning process is important; cannot be solved by simple memorization
- Require deep thinking for {params.thinking_time} or more
- Include advanced technical terms and concepts
"""
        }
        
        return instructions[difficulty]
    
    def adjust_question_complexity(
        self, 
        slide_content: Dict[str, Any], 
        difficulty: DifficultyLevel
    ) -> Dict[str, Any]:
        """Adjust question complexity based on slide content"""
        
        adjusted_content = slide_content.copy()
        params = self.difficulty_parameters[difficulty]
        
        # Adjust focus areas according to difficulty
        if difficulty == DifficultyLevel.EASY:
            # Focus on basic facts and definitions
            adjusted_content["focus_areas"] = [
                "Definition of basic terms",
                "Clearly stated facts",
                "Simple concepts"
            ]
            adjusted_content["question_patterns"] = [
                "What is ...?",
                "Which is the correct definition of ...?",
                "Which statement about ... is correct?"
            ]
        
        elif difficulty == DifficultyLevel.MEDIUM:
            # Focus on concept relationships and application
            adjusted_content["focus_areas"] = [
                "Relationships between concepts",
                "Practical examples",
                "Comparison and contrast"
            ]
            adjusted_content["question_patterns"] = [
                "Which is the correct relationship between ... and ...?",
                "How would you apply ... in practice?",
                "Which is an appropriate example of ...?"
            ]
        
        else:  # HARD
            # Focus on critical thinking and integration
            adjusted_content["focus_areas"] = [
                "Complex concept integration",
                "Critical analysis",
                "Creative problem solving"
            ]
            adjusted_content["question_patterns"] = [
                "Critically analyze ...?",
                "What are the problems and improvements for ...?",
                "How can ... be evaluated from another perspective?"
            ]
        
        return adjusted_content
    
    def calculate_difficulty_distribution(
        self, 
        total_questions: int,
        target_distribution: Dict[str, float] = None
    ) -> Dict[DifficultyLevel, int]:
        """Calculate difficulty distribution"""
        
        if target_distribution is None:
            target_distribution = {
                "easy": 0.4,      # 40%
                "medium": 0.4,    # 40%  
                "hard": 0.2       # 20%
            }
        
        distribution = {}
        remaining_questions = total_questions
        
        # Allocate easy questions
        easy_count = int(total_questions * target_distribution["easy"])
        distribution[DifficultyLevel.EASY] = easy_count
        remaining_questions -= easy_count
        
        # Allocate medium questions
        medium_count = int(total_questions * target_distribution["medium"])
        distribution[DifficultyLevel.MEDIUM] = medium_count
        remaining_questions -= medium_count
        
        # Allocate the rest to hard questions
        distribution[DifficultyLevel.HARD] = remaining_questions
        
        logger.info(f"Difficulty distribution: Easy {easy_count}, Medium {medium_count}, Hard {remaining_questions}")
        
        return distribution
    
    def validate_difficulty_balance(
        self, 
        generated_questions: List[Any]
    ) -> Dict[str, Any]:
        """Validate the difficulty balance of generated questions"""
        
        difficulty_counts = {
            DifficultyLevel.EASY: 0,
            DifficultyLevel.MEDIUM: 0,
            DifficultyLevel.HARD: 0
        }
        
        total_questions = len(generated_questions)
        
        for question in generated_questions:
            difficulty = question.difficulty if hasattr(question, 'difficulty') else DifficultyLevel.MEDIUM
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] += 1
        
        # Calculate ratios
        difficulty_ratios = {
            level: count / total_questions if total_questions > 0 else 0
            for level, count in difficulty_counts.items()
        }
        
        # Evaluate balance
        balance_score = self._calculate_balance_score(difficulty_ratios)
        
        return {
            "total_questions": total_questions,
            "difficulty_counts": difficulty_counts,
            "difficulty_ratios": difficulty_ratios,
            "balance_score": balance_score,
            "is_balanced": balance_score >= 0.7
        }
    
    def _calculate_balance_score(self, ratios: Dict[DifficultyLevel, float]) -> float:
        """Calculate balance score (range 0-1)"""
        
        # Ideal distribution
        ideal_ratios = {
            DifficultyLevel.EASY: 0.4,
            DifficultyLevel.MEDIUM: 0.4,
            DifficultyLevel.HARD: 0.2
        }
        
        # Calculate difference for each difficulty
        differences = []
        for level in DifficultyLevel:
            diff = abs(ratios.get(level, 0) - ideal_ratios[level])
            differences.append(diff)
        
        # Calculate score from average difference (smaller difference = higher score)
        avg_difference = sum(differences) / len(differences)
        balance_score = max(0, 1 - (avg_difference * 2))  # Multiply by 2 for sensitivity
        
        return balance_score
    
    def suggest_difficulty_adjustments(
        self, 
        current_distribution: Dict[DifficultyLevel, int],
        target_distribution: Dict[DifficultyLevel, int]
    ) -> List[str]:
        """Generate suggestions for difficulty adjustment"""
        
        suggestions = []
        
        for level in DifficultyLevel:
            current = current_distribution.get(level, 0)
            target = target_distribution.get(level, 0)
            
            if current < target:
                suggestions.append(f"Add {target - current} more '{level.value}' questions")
            elif current > target:
                suggestions.append(f"Reduce {current - target} '{level.value}' questions")
        
        return suggestions