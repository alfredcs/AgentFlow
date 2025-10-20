"""
Example workflow using tool-calling agents
"""

import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import ToolAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType


def calculator(input_data):
    """Simple calculator tool"""
    expression = input_data.get("expression", "")
    try:
        result = eval(expression)  # Note: Use safe eval in production
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def web_search(input_data):
    """Mock web search tool"""
    query = input_data.get("query", "")
    # In production, integrate with actual search API
    return {
        "results": [
            f"Result 1 for '{query}'",
            f"Result 2 for '{query}'",
            f"Result 3 for '{query}'"
        ]
    }


async def main():
    """Run workflow with tool-calling agents"""
    
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Define tools
    tools = [
        {
            "name": "calculator",
            "description": "Perform mathematical calculations. Input should be a valid Python expression.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        },
        {
            "name": "web_search",
            "description": "Search the web for information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    # Tool handlers
    tool_handlers = {
        "calculator": calculator,
        "web_search": web_search
    }
    
    # Create workflow
    workflow = Workflow(WorkflowConfig(
        name="tool_workflow",
        description="Workflow using tools"
    ))
    
    # Create tool agent
    agent_config = AgentConfig(
        name="tool_agent",
        model_type=ModelType.SONNET_4,
        temperature=0.5,
        tools=tools
    )
    
    tool_agent = ToolAgent(
        config=agent_config,
        bedrock_client=bedrock,
        prompt_template="{task}",
        tool_handlers=tool_handlers
    )
    
    workflow.add_step(
        step_id="solve_with_tools",
        agent=tool_agent,
        inputs={
            "task": """
            Calculate the compound interest on $10,000 invested at 5% annual rate for 3 years.
            Use the formula: A = P(1 + r)^t where P=10000, r=0.05, t=3
            Then search for information about compound interest.
            """
        }
    )
    
    # Execute workflow
    print("Running tool-based workflow...\n")
    result = await workflow.execute()
    
    print("=== Tool Agent Results ===")
    print(result['results']['solve_with_tools'])
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
