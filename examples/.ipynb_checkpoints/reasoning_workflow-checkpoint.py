"""
Example workflow using different reasoning patterns
"""

import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import ReasoningAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.patterns.reasoning import (
    get_reasoning_pattern,
    ReasoningPatternType
)


async def main():
    """Demonstrate different reasoning patterns"""
    
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow
    workflow = Workflow(WorkflowConfig(
        name="reasoning_comparison",
        description="Compare different reasoning approaches"
    ))
    
    # Problem to solve
    problem = """
    A company has 100 employees. 60% work remotely, and 40% work in the office.
    Of the remote workers, 75% prefer flexible hours.
    Of the office workers, 50% prefer flexible hours.
    How many employees in total prefer flexible hours?
    """
    
    # Chain-of-Thought reasoning
    cot_agent = ReasoningAgent(
        config=AgentConfig(
            name="cot_reasoner",
            model_type=ModelType.SONNET_4_5,
            temperature=0.3
        ),
        bedrock_client=bedrock,
        reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
    )
    
    workflow.add_step(
        step_id="chain_of_thought",
        agent=cot_agent,
        inputs={"task": problem, "context": "Solve this step by step"}
    )
    
    # Plan-and-Solve reasoning
    plan_solve_agent = ReasoningAgent(
        config=AgentConfig(
            name="plan_solve_reasoner",
            model_type=ModelType.SONNET_4_5,
            temperature=0.3
        ),
        bedrock_client=bedrock,
        reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.PLAN_AND_SOLVE)
    )
    
    workflow.add_step(
        step_id="plan_and_solve",
        agent=plan_solve_agent,
        inputs={"task": problem, "context": "Create a plan first"}
    )
    
    # Reflection reasoning
    reflection_agent = ReasoningAgent(
        config=AgentConfig(
            name="reflection_reasoner",
            model_type=ModelType.SONNET_4_5,
            temperature=0.3
        ),
        bedrock_client=bedrock,
        reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.REFLECTION)
    )
    
    workflow.add_step(
        step_id="reflection",
        agent=reflection_agent,
        inputs={"task": problem, "context": "Solve and reflect on your answer"}
    )
    
    # Execute workflow
    print("Comparing reasoning patterns...\n")
    result = await workflow.execute()
    
    print("=== Chain-of-Thought Result ===")
    print(result['results']['chain_of_thought'])
    print("\n=== Plan-and-Solve Result ===")
    print(result['results']['plan_and_solve'])
    print("\n=== Reflection Result ===")
    print(result['results']['reflection'])
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
