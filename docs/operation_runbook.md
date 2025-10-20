# Operation Runbook

This runbook provides operational procedures for deploying, monitoring, and troubleshooting AgentFlow in production environments.

## Table of Contents

1. [Deployment](#deployment)
2. [Monitoring](#monitoring)
3. [Troubleshooting](#troubleshooting)
4. [Maintenance](#maintenance)
5. [Incident Response](#incident-response)
6. [Performance Tuning](#performance-tuning)

---

## Deployment

### Prerequisites Checklist

- [ ] AWS Account with Bedrock access
- [ ] IAM roles and permissions configured
- [ ] Claude Sonnet 4 and Haiku 4.5 model access enabled
- [ ] CloudWatch Logs configured
- [ ] Python 3.10+ runtime environment
- [ ] Network connectivity to AWS services

### Deployment Steps

#### 1. Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install AgentFlow
pip install -e .
```

#### 2. AWS Configuration

```bash
# Configure AWS credentials
aws configure

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test model access
aws bedrock invoke-model \
    --model-id anthropic.claude-haiku-4-5-20250514 \
    --body '{"anthropic_version":"bedrock-2023-05-31","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}' \
    --region us-east-1 \
    output.json
```

#### 3. IAM Permissions

Create IAM policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-*"
            ]
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/aws/agentflow/*"
        }
    ]
}
```

#### 4. Environment Variables

Create `.env` file:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# AgentFlow Configuration
AGENTFLOW_LOG_LEVEL=INFO
AGENTFLOW_MAX_RETRIES=3
AGENTFLOW_TIMEOUT=300

# Bedrock Configuration
BEDROCK_ENDPOINT_URL=  # Optional: custom endpoint
BEDROCK_MAX_CONNECTIONS=10
```

#### 5. Deployment Verification

```python
# test_deployment.py
import asyncio
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType

async def verify_deployment():
    try:
        bedrock = BedrockClient(region_name="us-east-1")
        
        workflow = Workflow(WorkflowConfig(name="deployment_test"))
        
        agent = SimpleAgent(
            config=AgentConfig(
                name="test_agent",
                model_type=ModelType.HAIKU_4_5
            ),
            bedrock_client=bedrock,
            prompt_template="Say 'Deployment successful!'"
        )
        
        workflow.add_step("test", agent, {})
        result = await workflow.execute()
        
        print("✓ Deployment verification successful")
        return True
    except Exception as e:
        print(f"✗ Deployment verification failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(verify_deployment())
```

Run verification:
```bash
python test_deployment.py
```

---

## Monitoring

### Key Metrics

#### 1. Workflow Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Workflow Success Rate | % of successful workflows | < 95% |
| Workflow Duration | Average execution time | > 5 minutes |
| Workflow Failure Rate | % of failed workflows | > 5% |
| Active Workflows | Currently running workflows | > 100 |

#### 2. Agent Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Agent Execution Time | Time per agent execution | > 30 seconds |
| Agent Retry Rate | % of executions requiring retry | > 10% |
| Agent Error Rate | % of failed executions | > 5% |

#### 3. Bedrock Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Model Invocation Latency | Time to get response | > 10 seconds |
| Token Usage | Input + output tokens | Monitor for cost |
| Throttling Rate | % of throttled requests | > 1% |
| Model Error Rate | % of failed invocations | > 2% |

### CloudWatch Dashboard

Create CloudWatch dashboard:

```json
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AgentFlow", "WorkflowSuccess", {"stat": "Sum"}],
                    [".", "WorkflowFailure", {"stat": "Sum"}]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "us-east-1",
                "title": "Workflow Success/Failure"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/Bedrock", "Invocations", {"stat": "Sum"}],
                    [".", "ModelInvocationLatency", {"stat": "Average"}]
                ],
                "period": 300,
                "region": "us-east-1",
                "title": "Bedrock Metrics"
            }
        }
    ]
}
```

### Log Monitoring

#### CloudWatch Logs Insights Queries

**Failed Workflows:**
```
fields @timestamp, workflow_id, workflow_name, error
| filter level = "ERROR" and @message like /workflow.*failed/
| sort @timestamp desc
| limit 20
```

**Slow Executions:**
```
fields @timestamp, workflow_id, step_id, execution_time
| filter execution_time > 30000
| sort execution_time desc
| limit 20
```

**Retry Analysis:**
```
fields @timestamp, step_id, attempt, error
| filter attempt > 1
| stats count() by step_id, error
| sort count desc
```

**Token Usage:**
```
fields @timestamp, model, input_tokens, output_tokens
| stats sum(input_tokens) as total_input, sum(output_tokens) as total_output by model
```

### Alerting

#### CloudWatch Alarms

**High Error Rate:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name agentflow-high-error-rate \
    --alarm-description "Alert when error rate exceeds 5%" \
    --metric-name WorkflowFailureRate \
    --namespace AgentFlow \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 5.0 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:agentflow-alerts
```

**High Latency:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name agentflow-high-latency \
    --alarm-description "Alert when latency exceeds 30s" \
    --metric-name WorkflowDuration \
    --namespace AgentFlow \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 30000 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:agentflow-alerts
```

---

## Troubleshooting

### Common Issues

#### Issue 1: "Model Access Denied"

**Symptoms:**
- Error: `AccessDeniedException: You don't have access to the model`
- Workflow fails immediately

**Diagnosis:**
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1 | grep claude

# Check IAM permissions
aws iam get-role-policy --role-name YourRole --policy-name YourPolicy
```

**Resolution:**
1. Go to AWS Console → Bedrock → Model access
2. Request access to Claude Sonnet 4 and Haiku 4.5
3. Wait for approval (usually instant for most accounts)
4. Verify access: `aws bedrock list-foundation-models`

#### Issue 2: "Throttling Errors"

**Symptoms:**
- Error: `ThrottlingException: Rate exceeded`
- Intermittent failures
- High retry rates

**Diagnosis:**
```python
# Check throttling in logs
fields @timestamp, error
| filter error like /ThrottlingException/
| stats count() by bin(5m)
```

**Resolution:**
1. Implement exponential backoff (already built-in)
2. Request quota increase in AWS Service Quotas
3. Distribute load across multiple regions
4. Use Haiku 4.5 for simple tasks (higher quotas)

#### Issue 3: "High Latency"

**Symptoms:**
- Workflows taking longer than expected
- Timeouts occurring

**Diagnosis:**
```python
# Analyze execution times
from agentflow.utils.logging import setup_logger
logger = setup_logger(__name__)

# Check logs for slow steps
fields @timestamp, step_id, execution_time
| filter execution_time > 10000
| sort execution_time desc
```

**Resolution:**
1. Enable parallel execution: `enable_parallel=True`
2. Use faster model (Haiku 4.5) for simple tasks
3. Reduce `max_tokens` if possible
4. Optimize prompts to be more concise
5. Check network connectivity to AWS

#### Issue 4: "Memory Issues"

**Symptoms:**
- Out of memory errors
- Process crashes

**Diagnosis:**
```bash
# Monitor memory usage
import psutil
print(f"Memory: {psutil.virtual_memory().percent}%")
```

**Resolution:**
1. Limit concurrent workflows
2. Clear large results after processing
3. Use streaming for large responses
4. Increase instance memory

#### Issue 5: "Workflow Hangs"

**Symptoms:**
- Workflow never completes
- No error messages

**Diagnosis:**
```python
# Check for circular dependencies
workflow._validate_workflow()

# Check timeout settings
print(workflow.config.timeout_seconds)
```

**Resolution:**
1. Verify no circular dependencies in workflow
2. Increase timeout: `timeout_seconds=600`
3. Check for deadlocks in parallel execution
4. Review agent execution logs

### Debug Mode

Enable detailed logging:

```python
import logging
from agentflow.utils.logging import setup_logger

# Set to DEBUG level
logging.basicConfig(level=logging.DEBUG)

# All operations will be logged in detail
```

### Health Checks

Implement health check endpoint:

```python
async def health_check():
    """Verify system health"""
    checks = {
        "bedrock_connectivity": False,
        "model_access": False,
        "cloudwatch_logs": False
    }
    
    try:
        # Test Bedrock
        bedrock = BedrockClient()
        response = await bedrock.invoke(
            ModelType.HAIKU_4_5,
            "test",
            max_tokens=10
        )
        checks["bedrock_connectivity"] = True
        checks["model_access"] = True
    except Exception as e:
        print(f"Bedrock check failed: {e}")
    
    return checks
```

---

## Maintenance

### Regular Tasks

#### Daily
- [ ] Review error logs
- [ ] Check alert notifications
- [ ] Monitor token usage and costs
- [ ] Verify workflow success rates

#### Weekly
- [ ] Analyze performance trends
- [ ] Review and optimize slow workflows
- [ ] Update dependencies if needed
- [ ] Review and rotate credentials

#### Monthly
- [ ] Capacity planning review
- [ ] Cost optimization analysis
- [ ] Security audit
- [ ] Update documentation

### Backup and Recovery

**Configuration Backup:**
```bash
# Backup workflow configurations
tar -czf agentflow-config-$(date +%Y%m%d).tar.gz config/

# Backup to S3
aws s3 cp agentflow-config-*.tar.gz s3://your-backup-bucket/
```

**Disaster Recovery:**
1. Maintain infrastructure as code (Terraform/CloudFormation)
2. Document all manual configuration steps
3. Test recovery procedures quarterly
4. Keep backup of IAM policies and roles

### Updates and Upgrades

**Dependency Updates:**
```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade boto3

# Update all dependencies
pip install --upgrade -r requirements.txt

# Test after updates
pytest tests/
```

**AgentFlow Updates:**
```bash
# Pull latest changes
git pull origin main

# Install updates
pip install -e .

# Run tests
pytest tests/

# Deploy to staging first
# Then production after validation
```

---

## Incident Response

### Severity Levels

**P0 - Critical**
- Complete service outage
- Data loss or corruption
- Security breach
- Response time: Immediate

**P1 - High**
- Partial service degradation
- High error rates (>20%)
- Performance severely impacted
- Response time: 15 minutes

**P2 - Medium**
- Minor service degradation
- Elevated error rates (5-20%)
- Non-critical feature unavailable
- Response time: 1 hour

**P3 - Low**
- Cosmetic issues
- Low error rates (<5%)
- Documentation issues
- Response time: Next business day

### Incident Response Procedure

1. **Detection**
   - Alert received or issue reported
   - Verify and classify severity

2. **Assessment**
   - Check CloudWatch metrics and logs
   - Identify affected components
   - Estimate impact

3. **Communication**
   - Notify stakeholders
   - Create incident ticket
   - Update status page

4. **Mitigation**
   - Apply immediate fixes
   - Implement workarounds
   - Roll back if necessary

5. **Resolution**
   - Deploy permanent fix
   - Verify resolution
   - Monitor for recurrence

6. **Post-Mortem**
   - Document incident
   - Identify root cause
   - Create action items
   - Update runbook

### Rollback Procedure

```bash
# 1. Identify last known good version
git log --oneline

# 2. Rollback code
git checkout <commit-hash>

# 3. Reinstall dependencies
pip install -r requirements.txt

# 4. Restart services
# (depends on deployment method)

# 5. Verify rollback
python test_deployment.py

# 6. Monitor for stability
# Check logs and metrics for 30 minutes
```

---

## Performance Tuning

### Optimization Strategies

#### 1. Model Selection

```python
# Use appropriate model for task complexity
def select_model(task_description):
    simple_keywords = ["summarize", "extract", "classify"]
    
    if any(kw in task_description.lower() for kw in simple_keywords):
        return ModelType.HAIKU_4_5  # Fast and cost-effective
    else:
        return ModelType.SONNET_4   # Complex reasoning
```

#### 2. Parallel Execution

```python
# Enable parallel execution for independent steps
workflow_config = WorkflowConfig(
    name="optimized_workflow",
    enable_parallel=True  # Execute independent steps concurrently
)
```

#### 3. Prompt Optimization

```python
# Concise prompts reduce latency and cost
# Bad: Long, verbose prompt
prompt = """
Please analyze the following data in great detail, considering all possible 
aspects and providing comprehensive insights about every single element...
"""

# Good: Concise, specific prompt
prompt = "Analyze this data and provide 3 key insights: {data}"
```

#### 4. Token Management

```python
# Adjust max_tokens based on expected response length
agent_config = AgentConfig(
    name="summary_agent",
    max_tokens=500,  # Sufficient for summary, saves cost
)
```

#### 5. Caching

```python
# Implement result caching for repeated queries
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_workflow_execution(workflow_key, inputs_hash):
    # Execute workflow only if not cached
    pass
```

### Performance Benchmarks

Target performance metrics:

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Workflow Success Rate | >99% | >95% | <95% |
| Average Latency (Simple) | <2s | <5s | >5s |
| Average Latency (Complex) | <10s | <20s | >20s |
| Retry Rate | <1% | <5% | >5% |
| Cost per 1K workflows | <$5 | <$10 | >$10 |

### Load Testing

```python
# load_test.py
import asyncio
import time
from agentflow import Workflow, WorkflowConfig

async def load_test(num_workflows=100):
    start_time = time.time()
    
    tasks = []
    for i in range(num_workflows):
        workflow = create_test_workflow(f"test_{i}")
        tasks.append(workflow.execute())
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start_time
    successes = sum(1 for r in results if not isinstance(r, Exception))
    
    print(f"Completed {num_workflows} workflows in {duration:.2f}s")
    print(f"Success rate: {successes/num_workflows*100:.1f}%")
    print(f"Throughput: {num_workflows/duration:.2f} workflows/second")

if __name__ == "__main__":
    asyncio.run(load_test())
```

---

## Contact and Escalation

### Support Contacts

- **On-Call Engineer**: [on-call rotation]
- **Team Lead**: [team lead contact]
- **AWS Support**: [AWS support case portal]

### Escalation Path

1. On-Call Engineer (immediate)
2. Team Lead (15 minutes)
3. Engineering Manager (30 minutes)
4. AWS Support (for AWS service issues)

### Useful Links

- [AWS Bedrock Console](https://console.aws.amazon.com/bedrock)
- [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/logs)
- [Service Health Dashboard](https://health.aws.amazon.com/health/status)
- [Internal Documentation](link-to-internal-docs)

---

## Appendix

### Useful Commands

```bash
# Check AWS credentials
aws sts get-caller-identity

# List Bedrock models
aws bedrock list-foundation-models --region us-east-1

# Tail CloudWatch logs
aws logs tail /aws/agentflow/production --follow

# Check service quotas
aws service-quotas list-service-quotas --service-code bedrock

# Export metrics
aws cloudwatch get-metric-statistics \
    --namespace AgentFlow \
    --metric-name WorkflowSuccess \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

### Configuration Templates

See `config/` directory for:
- `workflow_config.yaml`: Workflow configuration template
- `agent_config.yaml`: Agent configuration template
- `deployment_config.yaml`: Deployment configuration template
