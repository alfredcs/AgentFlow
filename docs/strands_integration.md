# Amazon Strands SDK Integration

This document describes how AgentFlow integrates with Amazon Strands SDK for production-ready agent orchestration.

## Overview

AgentFlow uses Amazon Strands SDK patterns to provide:

- **Fault Tolerance**: Automatic retry with exponential backoff
- **CloudWatch Logging**: Structured logging to AWS CloudWatch
- **Execution Tracking**: Comprehensive metrics and observability
- **Production Ready**: Enterprise-grade reliability

## Architecture

### Strands SDK Integration Points

```
┌─────────────────────────────────────────────────────────┐
│                   AgentFlow Application                  │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│              StrandsWorkflow (Orchestration)             │
│  - Dependency resolution                                 │
│  - Parallel execution                                    │
│  - Automatic retry                                       │
│  - CloudWatch logging                                    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│              StrandsAgent (Execution Units)              │
│  - Fault tolerance                                       │
│  - Retry logic                                           │
│  - Metrics tracking                                      │
│  - CloudWatch logging                                    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│              Amazon Bedrock (AI Models)                  │
│  - Claude Sonnet 4                                       │
│  - Claude Haiku 4.5                                      │
└─────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Automatic Retry with Exponential Backoff

Both workflows and agents implement automatic retry:

```python
from agentflow import Workflow, WorkflowConfig, AgentConfig

# Workflow-level retry
workflow_config = WorkflowConfig(
    name="my_workflow",
    max_retries=3  # Retry failed steps up to 3 times
)

# Agent-level retry
agent_config = AgentConfig(
    name="my_agent",
    max_retries=3  # Retry agent execution up to 3 times
)
```

**Retry Strategy:**
- Exponential backoff: 2s, 4s, 8s
- Configurable max attempts
- Automatic on transient failures
- Logged to CloudWatch

### 2. CloudWatch Logging

Structured JSON logging to AWS CloudWatch:

```python
import os

# Enable CloudWatch logging
os.environ["CLOUDWATCH_ENABLED"] = "true"
os.environ["CLOUDWATCH_LOG_GROUP"] = "/aws/agentflow/production"
os.environ["CLOUDWATCH_STREAM_NAME"] = "workflow"
os.environ["AGENTFLOW_LOG_LEVEL"] = "INFO"
```

**Log Structure:**
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "agentflow.core.workflow",
  "workflow_id": "uuid",
  "workflow_name": "my_workflow",
  "message": "Workflow execution started",
  "step_count": 3
}
```

### 3. Execution Metrics

Comprehensive metrics tracking:

```python
result = await workflow.execute()

# Workflow metrics
print(result['metrics'])
# {
#   "total_steps": 3,
#   "completed_steps": 3,
#   "failed_steps": 0,
#   "retried_steps": 1,
#   "execution_time": 12.5
# }

# Agent metrics
for step_id, step in workflow.steps.items():
    metrics = step.agent.get_metrics()
    print(f"{step_id}: {metrics}")
# {
#   "agent_id": "uuid",
#   "agent_name": "my_agent",
#   "execution_count": 5,
#   "success_count": 4,
#   "failure_count": 1,
#   "success_rate": 0.8
# }
```

### 4. Fault Tolerance

Multiple layers of fault tolerance:

**Workflow Level:**
- Validates workflow before execution
- Detects circular dependencies
- Handles step failures gracefully
- Automatic retry of failed workflows

**Agent Level:**
- Input validation
- Timeout handling
- Automatic retry on failures
- Graceful error handling

**Bedrock Level:**
- Connection retry
- Throttling handling
- Error classification
- Automatic backoff

## Usage Examples

### Basic Workflow with Strands Integration

```python
import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType

async def main():
    # Initialize
    bedrock = BedrockClient(region_name="us-east-1")
    
    # Create workflow with fault tolerance
    workflow = Workflow(WorkflowConfig(
        name="strands_workflow",
        max_retries=3,
        timeout_seconds=300
    ))
    
    # Create agent
    agent = SimpleAgent(
        config=AgentConfig(
            name="my_agent",
            model_type=ModelType.HAIKU_4_5,
            max_retries=3
        ),
        bedrock_client=bedrock,
        prompt_template="Process: {input}"
    )
    
    # Add step
    workflow.add_step("step1", agent, {"input": "data"})
    
    # Execute with automatic retry and logging
    result = await workflow.execute()
    
    # Check metrics
    print(f"Execution time: {result['execution_time']}s")
    print(f"Metrics: {result['metrics']}")

asyncio.run(main())
```

### CloudWatch Logging Setup

```python
import os
import logging

# Configure CloudWatch
os.environ["CLOUDWATCH_ENABLED"] = "true"
os.environ["CLOUDWATCH_LOG_GROUP"] = "/aws/agentflow/production"
os.environ["CLOUDWATCH_STREAM_NAME"] = "my-workflow"
os.environ["AGENTFLOW_LOG_LEVEL"] = "INFO"

# Logs will automatically go to CloudWatch
from agentflow import Workflow, WorkflowConfig

workflow = Workflow(WorkflowConfig(name="my_workflow"))
# All workflow operations are logged to CloudWatch
```

### Error Handling with Strands Patterns

```python
from agentflow.utils.exceptions import WorkflowError, AgentExecutionError

try:
    result = await workflow.execute()
except AgentExecutionError as e:
    # Agent failed after all retries
    print(f"Agent execution failed: {e}")
    # Check CloudWatch for detailed logs
except WorkflowError as e:
    # Workflow-level error
    print(f"Workflow failed: {e}")
    # Check execution history
    print(workflow.execution_history)
```

## CloudWatch Integration

### Log Groups

AgentFlow creates the following log structure:

```
/aws/agentflow/
├── production/
│   ├── workflow-{workflow_id}
│   └── agent-{agent_id}
├── staging/
│   └── ...
└── development/
    └── ...
```

### Log Queries

**Find Failed Workflows:**
```
fields @timestamp, workflow_id, workflow_name, error
| filter level = "ERROR" and message like /workflow.*failed/
| sort @timestamp desc
```

**Track Execution Times:**
```
fields @timestamp, workflow_id, execution_time
| filter message like /completed successfully/
| stats avg(execution_time), max(execution_time) by workflow_name
```

**Monitor Retry Rates:**
```
fields @timestamp, step_id, attempt
| filter attempt > 1
| stats count() by step_id
```

## Configuration

### Environment Variables

```bash
# CloudWatch Configuration
CLOUDWATCH_ENABLED=true
CLOUDWATCH_LOG_GROUP=/aws/agentflow/production
CLOUDWATCH_STREAM_NAME=workflow

# Logging Configuration
AGENTFLOW_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default
```

### Workflow Configuration

```python
from agentflow import WorkflowConfig

config = WorkflowConfig(
    name="my_workflow",
    description="Workflow description",
    max_retries=3,              # Retry attempts per step
    timeout_seconds=300,        # Overall timeout
    enable_parallel=True,       # Enable parallel execution
    log_level="INFO"            # Logging verbosity
)
```

### Agent Configuration

```python
from agentflow import AgentConfig

config = AgentConfig(
    name="my_agent",
    model_type=ModelType.SONNET_4,
    temperature=0.7,
    max_tokens=4096,
    max_retries=3,              # Agent-level retries
    retry_delay=1.0             # Initial retry delay
)
```

## Monitoring

### Key Metrics to Monitor

1. **Workflow Success Rate**: % of successful workflows
2. **Execution Time**: Average and P95 execution time
3. **Retry Rate**: % of steps requiring retry
4. **Error Rate**: % of failed executions
5. **Token Usage**: Input and output tokens

### CloudWatch Alarms

```python
# Example: High error rate alarm
aws cloudwatch put-metric-alarm \
    --alarm-name agentflow-high-error-rate \
    --metric-name WorkflowFailureRate \
    --namespace AgentFlow \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 5.0 \
    --comparison-operator GreaterThanThreshold
```

## Best Practices

### 1. Use Appropriate Retry Counts

```python
# For critical operations
config = WorkflowConfig(max_retries=5)

# For non-critical operations
config = WorkflowConfig(max_retries=2)
```

### 2. Set Realistic Timeouts

```python
# For quick operations
config = WorkflowConfig(timeout_seconds=60)

# For complex workflows
config = WorkflowConfig(timeout_seconds=600)
```

### 3. Enable CloudWatch in Production

```python
# Always enable in production
os.environ["CLOUDWATCH_ENABLED"] = "true"

# Use appropriate log groups
os.environ["CLOUDWATCH_LOG_GROUP"] = "/aws/agentflow/production"
```

### 4. Monitor Metrics

```python
# Always check execution metrics
result = await workflow.execute()
if result['metrics']['failed_steps'] > 0:
    # Investigate failures
    print(result['execution_history'])
```

### 5. Handle Errors Gracefully

```python
try:
    result = await workflow.execute()
except WorkflowError as e:
    # Log to monitoring system
    logger.error("Workflow failed", error=str(e))
    # Implement fallback logic
    await fallback_workflow.execute()
```

## Troubleshooting

### Issue: CloudWatch Logs Not Appearing

**Solution:**
1. Check IAM permissions for CloudWatch Logs
2. Verify `CLOUDWATCH_ENABLED=true`
3. Check log group exists
4. Verify AWS credentials

### Issue: High Retry Rates

**Solution:**
1. Check CloudWatch logs for error patterns
2. Increase timeout if needed
3. Review Bedrock quotas
4. Check network connectivity

### Issue: Slow Execution

**Solution:**
1. Enable parallel execution
2. Use Haiku 4.5 for simple tasks
3. Reduce max_tokens
4. Optimize prompts

## References

- [Amazon Strands SDK](https://github.com/strands-agents/sdk-python)
- [AWS CloudWatch Logs](https://docs.aws.amazon.com/cloudwatch/logs/)
- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)
- [AgentFlow Documentation](../README.md)
