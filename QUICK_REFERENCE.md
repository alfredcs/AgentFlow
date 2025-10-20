# AgentFlow Quick Reference

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Basic Usage

### Create a Simple Workflow

```python
import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType

async def main():
    # Initialize Bedrock
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow
    workflow = Workflow(WorkflowConfig(name="my_workflow"))
    
    # Create agent
    agent = SimpleAgent(
        config=AgentConfig(
            name="my_agent",
            model_type=ModelType.HAIKU_4_5
        ),
        bedrock_client=bedrock,
        prompt_template="Process: {input}"
    )
    
    # Add step
    workflow.add_step("step1", agent, {"input": "data"})
    
    # Execute
    result = await workflow.execute()
    print(result['results']['step1'])

asyncio.run(main())
```

## Model Selection

```python
# Fast, cost-effective (simple tasks)
ModelType.HAIKU_4_5

# Powerful reasoning (complex tasks)
ModelType.SONNET_4

# Automatic selection
model = bedrock.get_model_for_task("simple")  # or "complex"
```

## Workflow Patterns

### Sequential Steps

```python
workflow.add_step("step1", agent1, {"input": "data"})
workflow.add_step("step2", agent2, {}, dependencies=["step1"])
```

### Parallel Steps

```python
workflow.add_step("step1", agent1, {"data": "x"})
workflow.add_step("step2", agent2, {"data": "y"})
workflow.add_step("step3", agent3, {}, dependencies=["step1", "step2"])
```

## Reasoning Patterns

```python
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType

# Chain-of-Thought
pattern = get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)

# ReAct
pattern = get_reasoning_pattern(ReasoningPatternType.REACT)

# Tree-of-Thought
pattern = get_reasoning_pattern(ReasoningPatternType.TREE_OF_THOUGHT)

# Reflection
pattern = get_reasoning_pattern(ReasoningPatternType.REFLECTION)

# Plan-and-Solve
pattern = get_reasoning_pattern(ReasoningPatternType.PLAN_AND_SOLVE)
```

## Agent Types

### SimpleAgent

```python
agent = SimpleAgent(
    config=AgentConfig(name="simple"),
    bedrock_client=bedrock,
    prompt_template="Task: {task}"
)
```

### ToolAgent

```python
tools = [{
    "name": "calculator",
    "description": "Perform calculations",
    "input_schema": {...}
}]

agent = ToolAgent(
    config=AgentConfig(name="tool_agent", tools=tools),
    bedrock_client=bedrock,
    prompt_template="{task}",
    tool_handlers={"calculator": calculator_function}
)
```

### ReasoningAgent

```python
agent = ReasoningAgent(
    config=AgentConfig(name="reasoner"),
    bedrock_client=bedrock,
    reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
)
```

## Configuration

### WorkflowConfig

```python
config = WorkflowConfig(
    name="workflow_name",
    max_retries=3,              # Retry attempts
    timeout_seconds=300,        # Timeout
    enable_parallel=True,       # Parallel execution
    log_level="INFO"            # Logging level
)
```

### AgentConfig

```python
config = AgentConfig(
    name="agent_name",
    model_type=ModelType.SONNET_4,
    temperature=0.7,            # 0.0-1.0
    max_tokens=4096,            # Max response length
    system_prompt="You are...", # System instructions
)
```

## Error Handling

```python
from agentflow.utils.exceptions import WorkflowError, AgentExecutionError

try:
    result = await workflow.execute()
except WorkflowError as e:
    print(f"Workflow failed: {e}")
except AgentExecutionError as e:
    print(f"Agent failed: {e}")
```

## Logging

```python
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)
logger.info("Message", key="value")
logger.error("Error", error=str(e), exc_info=True)
```

## Environment Variables

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=default

# AgentFlow Configuration
export AGENTFLOW_LOG_LEVEL=INFO
export AGENTFLOW_MAX_RETRIES=3
```

## Common Commands

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Format code
make format

# Run linters
make lint

# Run example
python examples/basic_workflow.py

# Deploy
./scripts/deploy.sh
```

## AWS Setup

```bash
# Configure AWS
aws configure

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test model
aws bedrock invoke-model \
    --model-id anthropic.claude-haiku-4-5-20250514 \
    --body '{"anthropic_version":"bedrock-2023-05-31","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}' \
    --region us-east-1 \
    output.json
```

## Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check workflow status
print(workflow.status)

# Check execution history
result = await workflow.execute()
for event in result['execution_history']:
    print(event)
```

## Performance Tips

1. Use Haiku 4.5 for simple tasks (faster, cheaper)
2. Enable parallel execution for independent steps
3. Reduce max_tokens for shorter responses
4. Use concise prompts
5. Implement result caching for repeated queries

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Model access denied | Enable in Bedrock console |
| Throttling errors | Request quota increase |
| High latency | Enable parallel execution |
| Import errors | Run `pip install -r requirements.txt` |
| AWS credentials | Run `aws configure` |

## File Locations

- **Examples**: `examples/`
- **Documentation**: `docs/`
- **Tests**: `tests/`
- **Configuration**: `config/`
- **Source Code**: `src/agentflow/`

## Resources

- Getting Started: `docs/getting_started.md`
- Architecture: `docs/architecture_design.md`
- Operations: `docs/operation_runbook.md`
- API Reference: `docs/api_reference.md`

## Support

- GitHub Issues: Report bugs
- Documentation: See `docs/` directory
- Examples: See `examples/` directory
