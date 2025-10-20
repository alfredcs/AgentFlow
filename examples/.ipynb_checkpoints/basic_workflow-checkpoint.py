"""
Basic workflow example using AgentFlow
"""

import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType


async def main():
    """Run a basic multi-step workflow"""
    
    # Initialize Bedrock client
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow
    workflow_config = WorkflowConfig(
        name="research_and_summarize",
        description="Research a topic and create a summary",
        max_retries=2,
        enable_parallel=True
    )
    workflow = Workflow(workflow_config)
    
    # Step 1: Research agent (uses Sonnet 4.5 for complex reasoning)
    research_config = AgentConfig(
        name="researcher",
        description="Research and gather information",
        model_type=ModelType.SONNET_4_5,
        temperature=0.7,
        reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
    )
    research_agent = SimpleAgent(
        config=research_config,
        bedrock_client=bedrock,
        prompt_template="Research the following topic and provide key findings: {topic}"
    )
    
    # Step 2: Summary agent (uses Haiku 4.5 for simple summarization)
    summary_config = AgentConfig(
        name="summarizer",
        description="Create concise summaries",
        model_type=ModelType.HAIKU_4_5,
        temperature=0.5,
        max_tokens=1000
    )
    summary_agent = SimpleAgent(
        config=summary_config,
        bedrock_client=bedrock,
        prompt_template="Summarize the following research in 3 bullet points:\n\n{research_result}"
    )
    
    # Add steps to workflow
    workflow.add_step(
        step_id="research",
        agent=research_agent,
        inputs={"topic": "Artificial Intelligence in Healthcare"}
    )
    
    workflow.add_step(
        step_id="summarize",
        agent=summary_agent,
        inputs={},
        dependencies=["research"]
    )
    
    # Execute workflow
    print("Starting workflow execution...")
    result = await workflow.execute()
    
    print("\n=== Workflow Results ===")
    print(f"Status: {result['status']}")
    print(f"\nResearch findings:\n{result['results']['research']}")
    print(f"\nSummary:\n{result['results']['summarize']}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
