# Strands SDK Integration - Quick Start

## What Changed?

AgentFlow now uses Amazon Strands SDK patterns for production-ready agent orchestration with:
- ✅ Automatic retry with exponential backoff
- ✅ CloudWatch Logs integration
- ✅ Comprehensive execution metrics
- ✅ Enhanced fault tolerance

**Good news**: Your existing code still works! All changes are backward compatible.

## Quick Start

### 1. Update Dependencies

```bash
pip install -r requirements.txt
```

New dependency: `watchtower>=3.0.0` (for CloudWatch logging)

### 2. Run Your Existing Code

```python
# Your existing code works without changes!
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType

async def main():
    bedrock = BedrockClient(region_name="us-east-1")
    workflow = Workflow(WorkflowConfig(name="my_workflow"))
    
    agent = SimpleAgent(
        config=AgentConfig(name="agent"),
        bedrock_client=bedrock,
        prompt_template="Process: {input}"
    )
    
    workflow.add_step("step1", agent, {"input": "data"})
    result = await workflow.execute()
    
    # NEW: Now includes metrics!
    print(f"Execution time: {result['execution_time']}s")
    print(f"Metrics: {result['metrics']}")
```

### 3. Enable CloudWatch Logging (Optional)

```python
import os

# Enable CloudWatch
os.environ["CLOUDWATCH_ENABLED"] = "true"
os.environ["CLOUDWATCH_LOG_GROUP"] = "/aws/agentflow/production"

# That's it! Logs now go to CloudWatch
```

### 4. Configure Retry (Optional)

```python
# Workflow-level retry
workflow = Workflow(WorkflowConfig(
    name="my_workflow",
    max_retries=3  # Retry failed steps up to 3 times
))

# Agent-level retry
agent = SimpleAgent(
    config=AgentConfig(
        name="agent",
        max_retries=3  # Retry agent execution up to 3 times
    ),
    bedrock_client=bedrock,
    prompt_template="Process: {input}"
)
```

## What You Get

### Automatic Retry

Failed operations automatically retry with exponential backoff:
- 1st retry: 2 seconds
- 2nd retry: 4 seconds
- 3rd retry: 8 seconds

### CloudWatch Logging

All operations logged to CloudWatch with:
- Workflow ID and name
- Step ID and agent name
- Execution timestamps
- Error details
- Execution metrics

### Execution Metrics

Every workflow execution returns metrics:

```python
result = await workflow.execute()

print(result['metrics'])
# {
#   "total_steps": 3,
#   "completed_steps": 3,
#   "failed_steps": 0,
#   "retried_steps": 1,
#   "execution_time": 12.5
# }
```

### Agent Metrics

Track agent performance:

```python
for step_id, step in workflow.steps.items():
    metrics = step.agent.get_metrics()
    print(f"{step_id}:")
    print(f"  Success rate: {metrics['success_rate']:.1%}")
    print(f"  Executions: {metrics['execution_count']}")
```

## Examples

### Run the New Example

```bash
python examples/strands_workflow_example.py
```

### Run Existing Examples

All existing examples still work:

```bash
python examples/basic_workflow.py
python examples/parallel_workflow.py
python examples/reasoning_workflow.py
python examples/tool_agent_workflow.py
```

## Configuration

### Environment Variables

```bash
# CloudWatch (Optional)
export CLOUDWATCH_ENABLED=true
export CLOUDWATCH_LOG_GROUP=/aws/agentflow/production
export CLOUDWATCH_STREAM_NAME=workflow

# Logging Level
export AGENTFLOW_LOG_LEVEL=INFO

# AWS
export AWS_REGION=us-east-1
```

### IAM Permissions for CloudWatch

```json
{
    "Effect": "Allow",
    "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
    ],
    "Resource": "arn:aws:logs:*:*:log-group:/aws/agentflow/*"
}
```

## Monitoring

### View CloudWatch Logs

```bash
# AWS Console
https://console.aws.amazon.com/cloudwatch/logs

# AWS CLI
aws logs tail /aws/agentflow/production --follow
```

### CloudWatch Queries

**Find Failed Workflows:**
```
fields @timestamp, workflow_id, error
| filter level = "ERROR"
| sort @timestamp desc
```

**Track Execution Times:**
```
fields @timestamp, execution_time
| stats avg(execution_time) by workflow_name
```

## Troubleshooting

### CloudWatch Logs Not Appearing

1. Check `CLOUDWATCH_ENABLED=true`
2. Verify IAM permissions
3. Check AWS credentials: `aws sts get-caller-identity`
4. Verify log group exists

### High Retry Rates

1. Check CloudWatch logs for error patterns
2. Increase timeout: `WorkflowConfig(timeout_seconds=600)`
3. Review Bedrock quotas
4. Check network connectivity

### Slow Execution

1. Enable parallel execution: `WorkflowConfig(enable_parallel=True)`
2. Use Haiku 4.5 for simple tasks
3. Reduce max_tokens
4. Optimize prompts

## Documentation

- [Complete Integration Guide](docs/strands_integration.md)
- [Integration Summary](STRANDS_INTEGRATION_SUMMARY.md)
- [Completion Report](STRANDS_REWRITE_COMPLETE.md)
- [Example Workflow](examples/strands_workflow_example.py)

## Key Points

✅ **No Breaking Changes**: All existing code works

✅ **Opt-In Features**: Enable CloudWatch when ready

✅ **Automatic Retry**: Built-in fault tolerance

✅ **Better Observability**: Metrics and logging

✅ **Production Ready**: Enterprise-grade reliability

## Next Steps

1. ✅ Update dependencies: `pip install -r requirements.txt`
2. ✅ Run existing code (it still works!)
3. ✅ Try the new example: `python examples/strands_workflow_example.py`
4. ✅ Enable CloudWatch logging (optional)
5. ✅ Monitor metrics and logs

## Questions?

- Check [Strands Integration Guide](docs/strands_integration.md)
- Review [examples/strands_workflow_example.py](examples/strands_workflow_example.py)
- See [Operation Runbook](docs/operation_runbook.md)

---

**Status**: ✅ Ready to Use

**Backward Compatible**: ✅ Yes (100%)

**Production Ready**: ✅ Yes
