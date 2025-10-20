"""
Reasoning patterns for structured agent thinking
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from enum import Enum


class ReasoningPatternType(Enum):
    """Types of reasoning patterns"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    REACT = "react"
    TREE_OF_THOUGHT = "tree_of_thought"
    REFLECTION = "reflection"
    PLAN_AND_SOLVE = "plan_and_solve"


class ReasoningPattern(ABC):
    """Base class for reasoning patterns"""
    
    @abstractmethod
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        """Apply the reasoning pattern to the prompt"""
        pass


class ChainOfThoughtPattern(ReasoningPattern):
    """
    Chain-of-Thought reasoning pattern
    
    Encourages step-by-step reasoning before arriving at an answer.
    """
    
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        cot_instruction = """
Let's approach this step-by-step:

1. First, understand the problem clearly
2. Break down the problem into smaller parts
3. Solve each part systematically
4. Combine the solutions
5. Verify the final answer

Think through each step carefully before providing your final answer.
"""
        return f"{cot_instruction}\n\n{prompt}\n\nProvide your step-by-step reasoning:"


class ReActPattern(ReasoningPattern):
    """
    ReAct (Reasoning + Acting) pattern
    
    Combines reasoning traces with task-specific actions.
    """
    
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        react_instruction = """
Use the following format:

Thought: Consider what you need to do
Action: The action to take
Observation: What you observe from the action
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: The final answer to the original question

Begin!
"""
        return f"{react_instruction}\n\nQuestion: {prompt}"


class TreeOfThoughtPattern(ReasoningPattern):
    """
    Tree-of-Thought reasoning pattern
    
    Explores multiple reasoning paths and evaluates them.
    """
    
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        tot_instruction = """
Explore multiple approaches to solve this problem:

For each approach:
1. Describe the approach
2. List pros and cons
3. Evaluate feasibility (score 1-10)

After exploring all approaches, select the best one and provide the solution.
"""
        return f"{tot_instruction}\n\nProblem: {prompt}"


class ReflectionPattern(ReasoningPattern):
    """
    Reflection pattern
    
    Encourages self-critique and refinement of answers.
    """
    
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        reflection_instruction = """
Solve the problem, then reflect on your solution:

1. Initial Solution: Provide your first answer
2. Reflection: Critique your solution - what could be wrong or improved?
3. Refined Solution: Provide an improved answer based on your reflection

Be critical and thorough in your reflection.
"""
        return f"{reflection_instruction}\n\nProblem: {prompt}"


class PlanAndSolvePattern(ReasoningPattern):
    """
    Plan-and-Solve pattern
    
    Creates a plan first, then executes it step by step.
    """
    
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        plan_solve_instruction = """
Follow this two-phase approach:

Phase 1 - Planning:
- Understand the problem requirements
- Identify key information and constraints
- Create a step-by-step plan

Phase 2 - Execution:
- Execute each step of your plan
- Show your work for each step
- Verify the solution

Provide both your plan and execution clearly.
"""
        return f"{plan_solve_instruction}\n\nProblem: {prompt}"


def get_reasoning_pattern(pattern_type: ReasoningPatternType) -> ReasoningPattern:
    """Factory function to get reasoning pattern by type"""
    patterns = {
        ReasoningPatternType.CHAIN_OF_THOUGHT: ChainOfThoughtPattern(),
        ReasoningPatternType.REACT: ReActPattern(),
        ReasoningPatternType.TREE_OF_THOUGHT: TreeOfThoughtPattern(),
        ReasoningPatternType.REFLECTION: ReflectionPattern(),
        ReasoningPatternType.PLAN_AND_SOLVE: PlanAndSolvePattern(),
    }
    return patterns[pattern_type]
