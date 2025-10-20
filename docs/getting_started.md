# Getting Started with AgentFlow

This guide will help you get up and running with AgentFlow using Amazon Strands SDK and Amazon Bedrock.

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.10 or higher** installed
2. **AWS Account** with access to Amazon Bedrock
3. **AWS CLI** configured with appropriate credentials
4. **Model Access** enabled for Claude Sonnet 4 and Haiku 4.5 in Bedrock

## Installation

### 1. Clone or Install the Package

```bash
# If installing from source
git clone <repository-url>
cd agentflow

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### 2. Configure AWS Credentials

Ensure your AWS credentials are configured:

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### 3. Enable Bedrock Model Access

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access"
3. Request access to:
   - Claude Sonnet 4 (anthropic.claude-sonnet-4-20250514)
   - Claude Haiku 4.5 (anthropic.claude-haiku-4-5-20250514)

## Quick Start Example

Create your first workflow in 5 minutes:

```python
import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType

async def main():
    # Initialize Bedrock client
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow
    workflow = Workflow(WorkflowConfig(
        name="hello_agentflow",
        description="My first AgentFlow workflow"
    ))
    
    # Create an agent
    agent_config = AgentConfig(
        name="greeter",
        model_type=ModelType.HAIKU_4_5,
        temperature=0.7
    )
    
    agent = SimpleAgent(
        config=agent_config,
        bedrock_client=bedrock,
        prompt_template="Generate a friendly greeting for {name}"
    )
    
    # Add step to workflow
    workflow.add_step(
        step_id="greet",
        agent=agent,
        inputs={"name": "World"}
    )
    
    # Execute
    result = await workflow.execute()
    print(result['results']['greet'])

if __name__ == "__main__":
    asyncio.run(main())
```

Save this as `hello_agentflow.py` and run:

```bash
python hello_agentflow.py
```

## Core Concepts

### 1. Workflows

Workflows orchestrate multiple agents in a structured execution flow:

```python
workflow_config = WorkflowConfig(
    name="my_workflow",
    description="Description of what this workflow does",
    max_retries=3,              # Retry failed steps
    timeout_seconds=300,        # Overall timeout
    enable_parallel=True        # Enable parallel execution
)

workflow = Workflow(workflow_config)
```

### 2. Agents

Agents are the execution units that interact with Bedrock models:

```python
agent_config = AgentConfig(
    name="my_agent",
    description="What this agent does",
    model_type=ModelType.SONNET_4,  # or HAIKU_4_5
    temperature=0.7,
    max_tokens=4096
)
```

### 3. Model Selection

Choose the right model for your task:

- **Claude Sonnet 4**: Complex reasoning, analysis, creative tasks
- **Claude Haiku 4.5**: Simple tasks, fast responses, cost-effective

```python
# For complex tasks
model_type=ModelType.SONNET_4

# For simple tasks
model_type=ModelType.HAIKU_4_5
```

### 4. Reasoning Patterns

Apply structured reasoning to your agents:

```python
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType

agent_config = AgentConfig(
    name="reasoning_agent",
    reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
)
```

Available patterns:
- `CHAIN_OF_THOUGHT`: Step-by-step reasoning
- `REACT`: Reasoning + Acting
- `TREE_OF_THOUGHT`: Multiple reasoning paths
- `REFLECTION`: Self-critique and refinement
- `PLAN_AND_SOLVE`: Planning then execution

## Building Multi-Step Workflows

### Sequential Steps

Steps execute one after another:

```python
workflow.add_step("step1", agent1, {"input": "data"})
workflow.add_step("step2", agent2, {}, dependencies=["step1"])
workflow.add_step("step3", agent3, {}, dependencies=["step2"])
```

### Parallel Steps

Independent steps execute simultaneously:

```python
# These run in parallel
workflow.add_step("analyze_a", agent_a, {"data": "x"})
workflow.add_step("analyze_b", agent_b, {"data": "y"})
workflow.add_step("analyze_c", agent_c, {"data": "z"})

# This waits for all parallel steps
workflow.add_step(
    "synthesize",
    synthesis_agent,
    {},
    dependencies=["analyze_a", "analyze_b", "analyze_c"]
)
```

### Using Previous Results

Access results from previous steps:

```python
workflow.add_step("step1", agent1, {"input": "data"})

# step1_result is automatically available
workflow.add_step(
    "step2",
    agent2,
    {},  # Empty inputs
    dependencies=["step1"]
)

# In agent2's prompt template:
# "Process this data: {step1_result}"
```

## Error Handling

AgentFlow includes comprehensive error handling:

```python
try:
    result = await workflow.execute()
except WorkflowError as e:
    print(f"Workflow failed: {e}")
except AgentExecutionError as e:
    print(f"Agent execution failed: {e}")
except BedrockError as e:
    print(f"Bedrock error: {e}")
```

Automatic retries are configured per workflow:

```python
workflow_config = WorkflowConfig(
    name="resilient_workflow",
    max_retries=3  # Retry failed steps up to 3 times
)
```

## Logging

AgentFlow uses structured logging for observability:

```python
import logging
from agentflow.utils.logging import setup_logger

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Logs are automatically structured as JSON
# Compatible with CloudWatch Logs
```

## Next Steps

- Explore [Architecture Design](architecture_design.md) to understand the system
- Review [Operation Runbook](operation_runbook.md) for production deployment
- Check out more examples in the `examples/` directory
- Read the API reference for detailed documentation

## Common Issues

### Issue: "Model access denied"

**Solution**: Ensure you've requested and been granted access to Claude models in Bedrock console.

### Issue: "Credentials not found"

**Solution**: Configure AWS credentials using `aws configure` or environment variables.

### Issue: "Import errors"

**Solution**: Ensure all dependencies are installed: `pip install -r requirements.txt`

## Getting Help

- Check the [Operation Runbook](operation_runbook.md) for troubleshooting
- Review example code in `examples/` directory
- Check AWS Bedrock documentation for model-specific issues
