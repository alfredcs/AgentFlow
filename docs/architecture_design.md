# Architecture Design

This document describes the architecture of AgentFlow, an implementation of structured agentic workflows using Amazon Strands SDK and Amazon Bedrock.

## Overview

AgentFlow is designed as a production-ready framework for building complex multi-agent workflows with the following key characteristics:

- **Modular Architecture**: Clear separation of concerns
- **Fault Tolerance**: Comprehensive error handling and retry mechanisms
- **Observability**: Structured logging and metrics
- **Scalability**: Support for parallel execution
- **Type Safety**: Full type hints and validation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  (User Workflows, Business Logic, Custom Agents)            │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    AgentFlow Core                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Workflow   │  │    Agent     │  │   Patterns   │     │
│  │   Engine     │  │  Framework   │  │  (Reasoning) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                  Integration Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Bedrock    │  │   Strands    │  │   Logging    │     │
│  │   Client     │  │     SDK      │  │   & Metrics  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    AWS Services                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Bedrock    │  │  CloudWatch  │  │     IAM      │     │
│  │ (Claude AI)  │  │     Logs     │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Workflow Engine

**Location**: `src/agentflow/core/workflow.py`

The workflow engine orchestrates multi-step agent execution with:

#### Key Features:
- **Dependency Resolution**: Automatically determines execution order based on step dependencies
- **Parallel Execution**: Executes independent steps concurrently for performance
- **Retry Logic**: Automatic retry with exponential backoff for failed steps
- **State Management**: Tracks workflow and step status throughout execution
- **Result Propagation**: Passes results between dependent steps

#### Workflow Lifecycle:

```
PENDING → RUNNING → COMPLETED
                 ↓
              FAILED
                 ↓
            CANCELLED
```

#### Execution Flow:

1. **Validation**: Check for circular dependencies and missing steps
2. **Dependency Resolution**: Create execution batches based on dependencies
3. **Execution**: Run batches sequentially, steps within batch in parallel
4. **Result Collection**: Gather and propagate results
5. **Error Handling**: Retry failed steps or fail workflow

### 2. Agent Framework

**Location**: `src/agentflow/core/agent.py`

Agents are the execution units that interact with AI models.

#### Agent Types:

**SimpleAgent**
- Template-based prompt generation
- Direct text responses
- Best for straightforward tasks

**ToolAgent**
- Function calling capabilities
- Tool execution and result handling
- Best for tasks requiring external actions

**ReasoningAgent**
- Structured reasoning patterns
- Step-by-step thinking
- Best for complex problem-solving

#### Agent Lifecycle:

```python
1. Initialize with config and Bedrock client
2. Receive inputs from workflow
3. Prepare prompt (apply reasoning pattern if configured)
4. Invoke Bedrock model
5. Process response
6. Return result to workflow
```

### 3. Bedrock Client

**Location**: `src/agentflow/models/bedrock_client.py`

Manages all interactions with Amazon Bedrock.

#### Features:
- **Model Abstraction**: Unified interface for different Claude models
- **Retry Logic**: Automatic retry with exponential backoff
- **Error Handling**: Comprehensive error classification and handling
- **Streaming Support**: Optional streaming responses
- **Model Selection**: Automatic model selection based on task complexity

#### Supported Models:

| Model | Use Case | Speed | Cost | Max Tokens |
|-------|----------|-------|------|------------|
| Claude Sonnet 4 | Complex reasoning, analysis | Medium | Higher | 200K |
| Claude Haiku 4.5 | Simple tasks, fast responses | Fast | Lower | 200K |

#### Request Flow:

```
Agent Request
    ↓
Prepare Request Body
    ↓
Invoke Bedrock API (with retry)
    ↓
Parse Response
    ↓
Return to Agent
```

### 4. Reasoning Patterns

**Location**: `src/agentflow/patterns/reasoning.py`

Structured reasoning patterns enhance agent capabilities.

#### Available Patterns:

**Chain-of-Thought (CoT)**
- Step-by-step reasoning
- Best for: Math, logic, analysis
- Example: "Let's solve this step by step..."

**ReAct (Reasoning + Acting)**
- Interleaved reasoning and actions
- Best for: Tasks requiring tools
- Format: Thought → Action → Observation

**Tree-of-Thought (ToT)**
- Multiple reasoning paths
- Best for: Complex decisions
- Explores and evaluates alternatives

**Reflection**
- Self-critique and refinement
- Best for: Quality-critical tasks
- Initial answer → Critique → Refined answer

**Plan-and-Solve**
- Planning before execution
- Best for: Multi-step problems
- Plan → Execute → Verify

### 5. Utilities

#### Logging (`src/agentflow/utils/logging.py`)

- **Structured Logging**: JSON-formatted logs
- **CloudWatch Compatible**: Direct integration with AWS CloudWatch
- **Context Binding**: Automatic context propagation
- **Log Levels**: Configurable verbosity

#### Exceptions (`src/agentflow/utils/exceptions.py`)

Custom exception hierarchy for precise error handling:

```
AgentFlowError (base)
├── WorkflowError
├── AgentExecutionError
├── BedrockError
│   └── ModelInvocationError
├── ConfigurationError
└── ValidationError
```

## Data Flow

### Single-Step Execution

```
User Input
    ↓
Workflow.add_step()
    ↓
Workflow.execute()
    ↓
Agent.execute()
    ↓
Agent._prepare_prompt()
    ↓
BedrockClient.invoke()
    ↓
[Amazon Bedrock]
    ↓
Agent._process_response()
    ↓
Return Result
```

### Multi-Step with Dependencies

```
Step A (no deps) ──┐
                   ├──> Execute in Parallel
Step B (no deps) ──┘
    ↓
Results A & B
    ↓
Step C (depends on A, B)
    ↓
Result C
```

## Configuration Management

### Workflow Configuration

```python
@dataclass
class WorkflowConfig:
    name: str                    # Workflow identifier
    description: str             # Human-readable description
    max_retries: int = 3        # Retry attempts per step
    timeout_seconds: int = 300  # Overall timeout
    enable_parallel: bool = True # Enable parallel execution
    log_level: str = "INFO"     # Logging verbosity
    metadata: Dict[str, Any]    # Custom metadata
```

### Agent Configuration

```python
@dataclass
class AgentConfig:
    name: str                           # Agent identifier
    description: str                    # Agent purpose
    model_type: ModelType              # Bedrock model to use
    temperature: float = 0.7           # Sampling temperature
    max_tokens: int = 4096             # Max response tokens
    system_prompt: Optional[str]       # System instructions
    reasoning_pattern: Optional[...]   # Reasoning pattern
    tools: List[Dict[str, Any]]       # Tool definitions
    metadata: Dict[str, Any]          # Custom metadata
```

## Error Handling Strategy

### Retry Logic

1. **Step-Level Retries**: Each step retries independently
2. **Exponential Backoff**: Wait time increases: 2s, 4s, 8s
3. **Max Attempts**: Configurable per workflow
4. **Failure Propagation**: Failed step fails entire workflow

### Error Recovery

```python
try:
    result = await workflow.execute()
except WorkflowError as e:
    # Workflow-level error (validation, dependencies)
    log_and_alert(e)
except AgentExecutionError as e:
    # Agent execution failed after retries
    log_and_retry_workflow(e)
except BedrockError as e:
    # Bedrock service error
    check_service_health(e)
```

## Observability

### Logging Strategy

**Structured Logs** with consistent fields:
- `timestamp`: ISO 8601 format
- `level`: INFO, WARNING, ERROR
- `workflow_id`: Unique workflow identifier
- `step_id`: Current step
- `agent_id`: Agent identifier
- `execution_id`: Unique execution identifier

### Metrics

Key metrics to monitor:
- Workflow success/failure rate
- Step execution time
- Model invocation latency
- Token usage (input/output)
- Retry frequency
- Error rates by type

### Tracing

Execution history captured in workflow results:
```python
{
    "workflow_id": "uuid",
    "status": "completed",
    "results": {...},
    "execution_history": [
        {
            "step_id": "step1",
            "status": "success",
            "attempt": 1,
            "result": "..."
        }
    ]
}
```

## Security Considerations

### AWS IAM Permissions

Required permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

### Data Protection

- **No Data Persistence**: Results not stored by framework
- **Encryption in Transit**: TLS for all AWS API calls
- **Credential Management**: Use IAM roles, not hardcoded keys
- **Input Validation**: Validate all user inputs

## Performance Optimization

### Model Selection

- Use **Haiku 4.5** for simple, fast tasks
- Use **Sonnet 4** for complex reasoning
- Automatic selection via `get_model_for_task()`

### Parallel Execution

- Enable with `enable_parallel=True`
- Automatically detects independent steps
- Reduces overall workflow time

### Caching Strategy

Consider implementing:
- Prompt caching for repeated patterns
- Result caching for idempotent operations
- Connection pooling for Bedrock client

## Scalability

### Horizontal Scaling

- Stateless design enables multiple instances
- Each workflow execution is independent
- Can run in Lambda, ECS, or EC2

### Vertical Scaling

- Adjust `max_tokens` based on task complexity
- Configure `timeout_seconds` for long-running tasks
- Tune `max_retries` for reliability vs. speed

## Extension Points

### Custom Agents

Extend the `Agent` base class:
```python
class CustomAgent(Agent):
    def _prepare_prompt(self, inputs):
        # Custom prompt logic
        pass
    
    def _process_response(self, response, inputs):
        # Custom response processing
        pass
```

### Custom Reasoning Patterns

Extend `ReasoningPattern`:
```python
class CustomPattern(ReasoningPattern):
    def apply(self, prompt, inputs):
        # Custom reasoning logic
        return modified_prompt
```

### Custom Tools

Add tools to agents:
```python
tools = [
    {
        "name": "calculator",
        "description": "Perform calculations",
        "input_schema": {...}
    }
]

agent_config = AgentConfig(
    name="tool_agent",
    tools=tools
)
```

## Future Enhancements

Potential improvements:
1. **Streaming Support**: Real-time response streaming
2. **Checkpoint/Resume**: Save and resume long workflows
3. **Dynamic Routing**: Route to different models based on content
4. **Cost Optimization**: Automatic model selection for cost
5. **Multi-Region**: Failover across AWS regions
6. **Batch Processing**: Process multiple workflows efficiently
7. **Human-in-the-Loop**: Pause for human approval
8. **A/B Testing**: Compare different agent configurations

## References

- [AgentFlow Paper](https://arxiv.org/pdf/2510.05592)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Strands SDK](https://github.com/strands-agents/sdk-python)
- [Claude Model Documentation](https://docs.anthropic.com/claude/docs)
