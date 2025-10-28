"""
Example workflow demonstrating Amazon Strands SDK integration

This example shows:
- Strands SDK patterns
- CloudWatch logging
- Fault tolerance
- Execution metrics

Supports multiple model types:
- Claude Sonnet 4.5 (ModelType.SONNET_4_5)
- Claude Haiku 4.5 (ModelType.HAIKU_4_5)
- Qwen 3-32B (ModelType.QWEN_3_32B)
"""

import asyncio
import os
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent_strands import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType


async def main():
    """Run a workflow with Strands SDK integration"""
    
    # Enable CloudWatch logging (optional)
    os.environ["CLOUDWATCH_ENABLED"] = "false"  # Set to "true" for CloudWatch
    os.environ["CLOUDWATCH_LOG_GROUP"] = "/aws/agentflow/examples"
    os.environ["AGENTFLOW_LOG_LEVEL"] = "INFO"
    
    print("=" * 60)
    print("AgentFlow with Amazon Strands SDK Integration")
    print("=" * 60)
    print()
    
    # Initialize Bedrock client
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow with fault tolerance
    workflow_config = WorkflowConfig(
        name="strands_demo_workflow",
        description="Demonstrates Strands SDK integration",
        max_retries=3,  # Automatic retry
        timeout_seconds=300,
        enable_parallel=True
    )
    workflow = Workflow(workflow_config)
    
    print("✓ Workflow initialized with Strands SDK patterns")
    print(f"  - Workflow ID: {workflow.workflow_id}")
    print(f"  - Max retries: {workflow_config.max_retries}")
    print(f"  - Timeout: {workflow_config.timeout_seconds}s")
    print()
    
    # Step 1: Analysis agent
    # Options: ModelType.SONNET_4_5, ModelType.HAIKU_4_5, ModelType.QWEN_3_32B
    analysis_config = AgentConfig(
        name="analyzer",
        description="Analyze data with fault tolerance",
        model_type=ModelType.SONNET_4_5,
        temperature=0.7,
        #max_retries=3
    )
    
    analysis_agent = SimpleAgent(
        config=analysis_config,
        bedrock_client=bedrock,
        prompt_template="Analyze the following topic and provide 3 key insights: {topic}"
    )
    
    workflow.add_step(
        step_id="analyze",
        agent=analysis_agent,
        inputs={"topic": "Cloud-native AI applications with Amazon Bedrock"}
    )
    
    print("✓ Added analysis step")
    
    # Step 2: Summary agent
    # Use HAIKU_4_5 or QWEN_3_32B for fast summarization
    summary_config = AgentConfig(
        name="summarizer",
        description="Create executive summary",
        model_type=ModelType.HAIKU_4_5,  # Fast model for simple task
        temperature=0.5,
        max_tokens=500
    )
    
    summary_agent = SimpleAgent(
        config=summary_config,
        bedrock_client=bedrock,
        prompt_template="Create a 2-sentence executive summary of: {analyze_result}"
    )
    
    workflow.add_step(
        step_id="summarize",
        agent=summary_agent,
        inputs={},
        dependencies=["analyze"]
    )
    
    print("✓ Added summary step")
    print()
    
    # Execute workflow
    print("Starting workflow execution...")
    print("-" * 60)
    
    try:
        result = await workflow.execute()
        
        print()
        print("=" * 60)
        print("Workflow Execution Results")
        print("=" * 60)
        print()
        
        print(f"Status: {result['status']}")
        print(f"Workflow ID: {result['workflow_id']}")
        #print(f"Execution Time: {result['execution_time']:.2f}s")
        print(f"Execution Result: {result['results']}")
        print()
        '''
        print("Metrics:")
        for key, value in result['metrics'].items():
            print(f"  - {key}: {value}")
        print()
        '''
        print("Analysis Results:")
        print("-" * 60)
        print(result['results']['analyze'])
        print()
        
        print("Executive Summary:")
        print("-" * 60)
        print(result['results']['summarize'])
        print()
        
        print("Execution History:")
        print("-" * 60)
        for event in result['execution_history']:
            print(f"  Step: {event['step_id']}")
            print(f"  Status: {event['status']}")
            print(f"  Attempts: {event.get('attempt', 1)}")
            if 'execution_time' in event:
                #print(f"  Time: {event['execution_time']:.2f}s")
                print(f"  Event: {event}")
            print()
        
        # Get agent metrics
        print("Agent Metrics:")
        print("-" * 60)
        for step_id, step in workflow.steps.items():
            metrics = step.agent.get_metrics()
            print(f"  {step_id}:")
            print(f"    - Executions: {metrics['execution_count']}")
            print(f"    - Success Rate: {metrics['success_rate']:.1%}")
        print()
        
        print("=" * 60)
        print("✓ Workflow completed successfully!")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print()
        print("=" * 60)
        print("Workflow Execution Failed")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("The workflow includes automatic retry and fault tolerance.")
        print("Check CloudWatch Logs for detailed error information.")
        raise


if __name__ == "__main__":
    asyncio.run(main())
