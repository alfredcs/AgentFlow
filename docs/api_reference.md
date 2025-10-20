# API Reference

Complete API documentation for AgentFlow.

## Core Classes

### Workflow

Main orchestration class for multi-step agent workflows.

```python
from agentflow import Workflow, WorkflowConfig

workflow = Workflow(config: WorkflowConfig)
```

#### Methods

**`add_step(step_id, agent, inputs, dependencies=None)`**

Add a step to the workflow.

- **step_id** (str): Unique identifier for the step
- **agent** (Agent): Agent to execute
- **inputs** (Dict[str, Any]): Input data for the agent
- **dependencies** (List[str], optional): List of step IDs this step depends on

Returns: `Workflow` (for chaining)

**`async execute()`**

Execute the workflow.

Returns: `Dict[str, Any]` containing:
- `workflow_id`: Unique workflow identifier
- `status`: Execution status
- `results`: Dictionary of step results
- `execution_history`: List of execution events

Raises:
- `WorkflowError`: If workflow validation or execution fails
- `AgentExecutionError`: If agent execution fails

#### Example

```python
workflow = Workflow(WorkflowConfig(name="my_workflow"))
workflow.add_step("step1", agent1, {"input": "data"})
workflow.add_step("step2", agent2, {}, dependencies=["step1"])
result = await workflow.execute()
```

---

### WorkflowConfig

Configuration for workflow execution.

```python
from agentflow import WorkflowConfig

config = WorkflowConfig(
    name: str,
    description: str = "",
    max_retries: int = 3,
    timeout_seconds: int = 300,
    enable_parallel: bool = True,
    log_level: str = "INFO",
    metadata: Dict[str, Any] = {}
)
```

#### Parameters

- **name** (str): Workflow name (required)
- **description** (str): Human-readable description
- **max_retries** (int): Maximum retry attempts per step (default: 3)
- **timeout_seconds** (int): Overall workflow timeout (default: 300)
- **enable_parallel** (bool): Enable parallel step execution (default: True)
- **log_level** (str): Logging level (default: "INFO")
- **metadata** (Dict): Custom metadata

---

### Agent

Base class for agents. Use subclasses for specific functionality.

#### Subclasses

**SimpleAgent**: Template-based agents for straightforward tasks
**ToolAgent**: Agents with tool-calling capabilities
**ReasoningAgent**: Agents with structured reasoning patterns

---

### SimpleAgent

Agent for straightforward tasks using template-based prompts.

```python
from agentflow.core.agent import SimpleAgent, AgentConfig
from agentflow.models.bedrock_client import BedrockClient

agent = SimpleAgent(
    config: AgentConfig,
    bedrock_client: BedrockClient,
    prompt_template: str
)
```

#### Parameters

- **config** (AgentConfig): Agent configuration
- **bedrock_client** (BedrockClient): Bedrock client instance
- **prompt_template** (str): Template string with {variable} placeholders

#### Example

```python
agent = SimpleAgent(
    config=AgentConfig(name="summarizer"),
    bedrock_client=bedrock,
    prompt_template="Summarize this text: {text}"
)
```

---

### ToolAgent

Agent with tool-calling capabilities.

```python
from agentflow.core.agent import ToolAgent, AgentConfig

agent = ToolAgent(
    config: AgentConfig,
    bedrock_client: BedrockClient,
    prompt_template: str,
    tool_handlers: Dict[str, Callable]
)
```

#### Parameters

- **config** (AgentConfig): Agent configuration with tools defined
- **bedrock_client** (BedrockClient): Bedrock client instance
- **prompt_template** (str): Template for the prompt
- **tool_handlers** (Dict[str, Callable]): Mapping of tool names to handler functions

#### Example

```python
def calculator(input_data):
    return {"result": eval(input_data["expression"])}

tools = [{
    "name": "calculator",
    "description": "Perform calculations",
    "input_schema": {...}
}]

agent = ToolAgent(
    config=AgentConfig(name="tool_agent", tools=tools),
    bedrock_client=bedrock,
    prompt_template="{task}",
    tool_handlers={"calculator": calculator}
)
```

---

### ReasoningAgent

Agent with structured reasoning patterns.

```python
from agentflow.core.agent import ReasoningAgent, AgentConfig
from agentflow.patterns.reasoning import ReasoningPattern

agent = ReasoningAgent(
    config: AgentConfig,
    bedrock_client: BedrockClient,
    reasoning_pattern: ReasoningPattern
)
```

#### Parameters

- **config** (AgentConfig): Agent configuration
- **bedrock_client** (BedrockClient): Bedrock client instance
- **reasoning_pattern** (ReasoningPattern): Reasoning pattern to apply

#### Example

```python
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType

agent = ReasoningAgent(
    config=AgentConfig(name="reasoner"),
    bedrock_client=bedrock,
    reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
)
```

---

### AgentConfig

Configuration for agents.

```python
from agentflow import AgentConfig
from agentflow.models.bedrock_client import ModelType

config = AgentConfig(
    name: str,
    description: str = "",
    model_type: ModelType = ModelType.SONNET_4,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    system_prompt: Optional[str] = None,
    reasoning_pattern: Optional[ReasoningPattern] = None,
    tools: List[Dict[str, Any]] = [],
    metadata: Dict[str, Any] = {}
)
```

#### Parameters

- **name** (str): Agent name (required)
- **description** (str): Agent description
- **model_type** (ModelType): Bedrock model to use
- **temperature** (float): Sampling temperature (0.0-1.0)
- **max_tokens** (int): Maximum tokens to generate
- **system_prompt** (str, optional): System instructions
- **reasoning_pattern** (ReasoningPattern, optional): Reasoning pattern
- **tools** (List[Dict], optional): Tool definitions
- **metadata** (Dict): Custom metadata

---

### BedrockClient

Client for Amazon Bedrock interactions.

```python
from agentflow.models.bedrock_client import BedrockClient

client = BedrockClient(
    region_name: str = "us-east-1",
    max_retries: int = 3,
    timeout: int = 300
)
```

#### Methods

**`async invoke(model_type, prompt, system_prompt=None, temperature=0.7, max_tokens=4096, tools=None, stop_sequences=None)`**

Invoke a Bedrock model.

- **model_type** (ModelType): Model to invoke
- **prompt** (str): User prompt
- **system_prompt** (str, optional): System instructions
- **temperature** (float): Sampling temperature
- **max_tokens** (int): Maximum tokens to generate
- **tools** (List[Dict], optional): Tool definitions
- **stop_sequences** (List[str], optional): Stop sequences

Returns: `Dict[str, Any]` with model response

Raises:
- `ModelInvocationError`: If invocation fails
- `BedrockError`: For other Bedrock errors

**`async invoke_with_streaming(model_type, prompt, system_prompt=None, temperature=0.7, max_tokens=4096)`**

Invoke model with streaming response.

Yields: Response chunks as they arrive

**`get_model_for_task(task_complexity)`**

Select appropriate model based on task complexity.

- **task_complexity** (str): "simple" or "complex"

Returns: `ModelType`

#### Example

```python
bedrock = BedrockClient(region_name="us-east-1")

response = await bedrock.invoke(
    model_type=ModelType.HAIKU_4_5,
    prompt="Hello, world!",
    temperature=0.7
)
```

---

### ModelType

Enum for supported Bedrock models.

```python
from agentflow.models.bedrock_client import ModelType

# Available models
ModelType.SONNET_4      # Claude Sonnet 4 - complex reasoning
ModelType.HAIKU_4_5     # Claude Haiku 4.5 - fast, simple tasks
```

---

## Reasoning Patterns

### ReasoningPattern

Base class for reasoning patterns.

#### Available Patterns

Get patterns using the factory function:

```python
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType

pattern = get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
```

#### Pattern Types

**`ReasoningPatternType.CHAIN_OF_THOUGHT`**

Step-by-step reasoning pattern. Best for math, logic, and analysis.

**`ReasoningPatternType.REACT`**

Reasoning + Acting pattern. Best for tasks requiring tools and actions.

**`ReasoningPatternType.TREE_OF_THOUGHT`**

Multiple reasoning paths. Best for complex decisions requiring exploration.

**`ReasoningPatternType.REFLECTION`**

Self-critique and refinement. Best for quality-critical tasks.

**`ReasoningPatternType.PLAN_AND_SOLVE`**

Planning before execution. Best for multi-step problems.

#### Example

```python
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType

# Get a reasoning pattern
cot_pattern = get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)

# Use in agent config
config = AgentConfig(
    name="reasoning_agent",
    reasoning_pattern=cot_pattern
)
```

---

## Utilities

### Logging

```python
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)

# Use structured logging
logger.info("Message", key1="value1", key2="value2")
logger.error("Error occurred", error=str(e), exc_info=True)
```

### Exceptions

```python
from agentflow.utils.exceptions import (
    AgentFlowError,        # Base exception
    WorkflowError,         # Workflow errors
    AgentExecutionError,   # Agent execution errors
    BedrockError,          # Bedrock client errors
    ModelInvocationError,  # Model invocation errors
    ConfigurationError,    # Configuration errors
    ValidationError        # Validation errors
)

try:
    result = await workflow.execute()
except WorkflowError as e:
    logger.error("Workflow failed", error=str(e))
except AgentExecutionError as e:
    logger.error("Agent failed", error=str(e))
```

---

## Type Hints

AgentFlow uses comprehensive type hints. Import types:

```python
from typing import Dict, List, Any, Optional
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import Agent
from agentflow.models.bedrock_client import BedrockClient, ModelType
```

---

## Advanced Usage

### Custom Agents

Create custom agents by extending the `Agent` base class:

```python
from agentflow.core.agent import Agent, AgentConfig

class CustomAgent(Agent):
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        # Custom prompt preparation logic
        return f"Custom prompt: {inputs}"
    
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        # Custom response processing
        return response.get("content", [{}])[0].get("text", "")
```

### Custom Reasoning Patterns

Create custom reasoning patterns:

```python
from agentflow.patterns.reasoning import ReasoningPattern

class CustomPattern(ReasoningPattern):
    def apply(self, prompt: str, inputs: Dict[str, Any]) -> str:
        # Custom reasoning logic
        return f"Custom reasoning:\n{prompt}"
```

### Workflow Hooks

Access workflow execution history:

```python
result = await workflow.execute()

for event in result['execution_history']:
    print(f"Step: {event['step_id']}")
    print(f"Status: {event['status']}")
    print(f"Attempts: {event.get('attempt', 1)}")
```

### Error Handling

Comprehensive error handling:

```python
from agentflow.utils.exceptions import WorkflowError, AgentExecutionError

try:
    result = await workflow.execute()
except WorkflowError as e:
    # Handle workflow-level errors
    logger.error("Workflow failed", error=str(e))
    # Implement retry or fallback logic
except AgentExecutionError as e:
    # Handle agent execution errors
    logger.error("Agent failed", error=str(e))
    # Implement agent-specific recovery
```

---

## Best Practices

1. **Model Selection**: Use Haiku 4.5 for simple tasks, Sonnet 4 for complex reasoning
2. **Parallel Execution**: Enable for independent steps to improve performance
3. **Error Handling**: Always wrap workflow execution in try-except blocks
4. **Logging**: Use structured logging for better observability
5. **Retries**: Configure appropriate retry counts based on task criticality
6. **Timeouts**: Set realistic timeouts based on expected execution time
7. **Prompts**: Keep prompts concise and specific for better results
8. **Tools**: Validate tool inputs and handle errors gracefully

---

## Examples

See the `examples/` directory for complete working examples:

- `basic_workflow.py`: Simple sequential workflow
- `parallel_workflow.py`: Parallel execution example
- `reasoning_workflow.py`: Different reasoning patterns
- `tool_agent_workflow.py`: Tool-calling agents

---

## Version History

### v0.1.0 (Current)

- Initial release
- Core workflow engine
- Bedrock integration
- Reasoning patterns
- Comprehensive logging
- Production-ready error handling
