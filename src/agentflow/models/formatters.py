"""
Data models and formatters for AgentFlow

Defines Pydantic models for structured data used across the AgentFlow system.
Works with all supported Bedrock models:
- Claude Sonnet 4.5 (ModelType.SONNET_4_5)
- Claude Haiku 4.5 (ModelType.HAIKU_4_5)
- Qwen 3-32B (ModelType.QWEN_3_32B)
"""

from pydantic import BaseModel

# Planner: QueryAnalysis
class QueryAnalysis(BaseModel):
    concise_summary: str
    required_skills: str
    relevant_tools: str
    additional_considerations: str

    def __str__(self):
        return f"""
Concise Summary: {self.concise_summary}

Required Skills:
{self.required_skills}

Relevant Tools:
{self.relevant_tools}

Additional Considerations:
{self.additional_considerations}
"""

# Planner: NextStep
class NextStep(BaseModel):
    justification: str
    context: str
    sub_goal: str
    tool_name: str

# Executor: MemoryVerification
class MemoryVerification(BaseModel):
    analysis: str
    stop_signal: bool

# Executor: ToolCommand
class ToolCommand(BaseModel):
    analysis: str
    explanation: str
    command: str
