"""
Example usage of the Planner with BedrockClient

Demonstrates how to use the rewritten Planner that uses BedrockClient
instead of create_llm_engine.
"""

import asyncio
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.models.planner_bedrock import Planner, Memory


async def main():
    """Demonstrate planner usage"""
    
    print("=" * 60)
    print("AgentFlow Planner Example with BedrockClient")
    print("=" * 60)
    print()
    
    # Initialize Bedrock client
    bedrock = BedrockClient(region_name="us-east-1")
    print("✓ Bedrock client initialized")
    
    # Define available tools
    available_tools = [
        "calculator",
        "web_search",
        "code_interpreter",
        "image_analyzer"
    ]
    
    # Define tool metadata
    toolbox_metadata = {
        "calculator": {
            "description": "Performs mathematical calculations",
            "limitations": "Cannot handle symbolic math"
        },
        "web_search": {
            "description": "Searches the web for information",
            "limitations": "Results may be outdated"
        },
        "code_interpreter": {
            "description": "Executes Python code",
            "limitations": "Sandboxed environment"
        },
        "image_analyzer": {
            "description": "Analyzes images and extracts information",
            "limitations": "Requires image input"
        }
    }
    
    # Create planner
    planner = Planner(
        bedrock_client=bedrock,
        model_type=ModelType.SONNET_4_5,  # Use Sonnet 4 for planning
        toolbox_metadata=toolbox_metadata,
        available_tools=available_tools,
        verbose=True,
        temperature=0.0  # Use 0 for deterministic planning
    )
    print("✓ Planner initialized")
    print(f"  - Model: {ModelType.SONNET_4_5.value}")
    print(f"  - Available tools: {len(available_tools)}")
    print()
    
    # Example 1: Generate base response
    print("-" * 60)
    print("Example 1: Generate Base Response")
    print("-" * 60)
    
    question1 = "What is the capital of France and what is its population?"
    print(f"Question: {question1}")
    print()
    
    base_response = await planner.generate_base_response(
        question=question1,
        max_tokens=500
    )
    print("Base Response:")
    print(base_response)
    print()
    
    # Example 2: Analyze query
    print("-" * 60)
    print("Example 2: Analyze Query")
    print("-" * 60)
    
    question2 = "Calculate the compound interest on $10,000 at 5% for 3 years, then search for current inflation rates"
    print(f"Question: {question2}")
    print()
    
    query_analysis = await planner.analyze_query(
        question=question2
    )
    print("Query Analysis:")
    print(query_analysis)
    print()
    
    # Example 3: Generate next step
    print("-" * 60)
    print("Example 3: Generate Next Step")
    print("-" * 60)
    
    memory = Memory()
    memory.add_action({
        "step": 1,
        "tool": "calculator",
        "action": "Calculate compound interest",
        "result": "$11,576.25"
    })
    
    next_step = await planner.generate_next_step(
        question=question2,
        image=None,
        query_analysis=query_analysis,
        memory=memory,
        step_count=2,
        max_step_count=5
    )
    print("Next Step:")
    print(next_step)
    print()
    
    # Extract components
    context, sub_goal, tool_name = planner.extract_context_subgoal_and_tool(next_step)
    if context and sub_goal and tool_name:
        print("Extracted Components:")
        print(f"  Context: {context[:100]}...")
        print(f"  Sub-Goal: {sub_goal}")
        print(f"  Tool: {tool_name}")
    print()
    
    # Example 4: Verify memory
    print("-" * 60)
    print("Example 4: Verify Memory")
    print("-" * 60)
    
    memory.add_action({
        "step": 2,
        "tool": "web_search",
        "action": "Search for current inflation rates",
        "result": "Current inflation rate is approximately 3.2%"
    })
    
    final_answer = "The compound interest on $10,000 at 5% for 3 years is $11,576.25. The current inflation rate is approximately 3.2%."
    
    is_verified = await planner.verify_memory(
        question=question2,
        memory=memory,
        final_answer=final_answer
    )
    print(f"Verification Result: {'✓ VERIFIED' if is_verified else '✗ NOT VERIFIED'}")
    print()
    
    # Example 5: Multi-step planning workflow
    print("-" * 60)
    print("Example 5: Multi-Step Planning Workflow")
    print("-" * 60)
    
    question3 = "What is 15% of 250, and then multiply that by 3?"
    print(f"Question: {question3}")
    print()
    
    # Analyze query
    analysis = await planner.analyze_query(question3)
    print("Analysis:")
    print(analysis[:200] + "...")
    print()
    
    # Simulate multi-step execution
    workflow_memory = Memory()
    max_steps = 5
    
    for step in range(1, max_steps + 1):
        print(f"\n--- Step {step} ---")
        
        # Generate next step
        next_step = await planner.generate_next_step(
            question=question3,
            image=None,
            query_analysis=analysis,
            memory=workflow_memory,
            step_count=step,
            max_step_count=max_steps
        )
        
        # Extract components
        context, sub_goal, tool = planner.extract_context_subgoal_and_tool(next_step)
        
        if tool and "FINISH" in tool.upper():
            print("✓ Workflow complete!")
            break
        
        if context and sub_goal and tool:
            print(f"Sub-Goal: {sub_goal}")
            print(f"Tool: {tool}")
            
            # Simulate tool execution
            if "calculator" in tool.lower():
                if step == 1:
                    result = "37.5"
                    workflow_memory.add_action({
                        "step": step,
                        "tool": tool,
                        "action": sub_goal,
                        "result": result
                    })
                    print(f"Result: {result}")
                elif step == 2:
                    result = "112.5"
                    workflow_memory.add_action({
                        "step": step,
                        "tool": tool,
                        "action": sub_goal,
                        "result": result
                    })
                    print(f"Result: {result}")
        else:
            print("Could not extract step components")
            break
    
    print()
    print("=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
