"""
Parallel workflow example with multiple independent agents
"""

import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType


async def main():
    """Run parallel analysis workflow"""
    
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow with parallel execution enabled
    workflow_config = WorkflowConfig(
        name="parallel_analysis",
        description="Analyze data from multiple perspectives in parallel",
        enable_parallel=True
    )
    workflow = Workflow(workflow_config)
    
    # Create multiple analysis agents that can run in parallel
    perspectives = [
        ("technical", "Analyze from a technical perspective"),
        ("business", "Analyze from a business perspective"),
        ("user", "Analyze from a user experience perspective")
    ]
    
    for perspective_name, description in perspectives:
        agent_config = AgentConfig(
            name=f"{perspective_name}_analyst",
            description=description,
            model_type=ModelType.HAIKU_4_5,  # Fast model for parallel execution
            temperature=0.7
        )
        
        agent = SimpleAgent(
            config=agent_config,
            bedrock_client=bedrock,
            prompt_template=f"{description}: {{product_description}}"
        )
        
        workflow.add_step(
            step_id=f"analyze_{perspective_name}",
            agent=agent,
            inputs={
                "product_description": "A new AI-powered mobile app for personal finance management"
            }
        )
    
    # Add synthesis step that depends on all analyses
    synthesis_config = AgentConfig(
        name="synthesizer",
        description="Synthesize multiple perspectives",
        model_type=ModelType.SONNET_4,  # Use powerful model for synthesis
        temperature=0.6
    )
    
    synthesis_agent = SimpleAgent(
        config=synthesis_config,
        bedrock_client=bedrock,
        prompt_template="""
Synthesize the following analyses into a comprehensive report:

Technical Analysis: {analyze_technical_result}

Business Analysis: {analyze_business_result}

User Analysis: {analyze_user_result}

Provide a balanced synthesis with recommendations.
"""
    )
    
    workflow.add_step(
        step_id="synthesize",
        agent=synthesis_agent,
        inputs={},
        dependencies=["analyze_technical", "analyze_business", "analyze_user"]
    )
    
    # Execute workflow
    print("Starting parallel workflow execution...")
    result = await workflow.execute()
    
    print("\n=== Workflow Results ===")
    print(f"Status: {result['status']}")
    print(f"\nFinal Synthesis:\n{result['results']['synthesize']}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
