# AgentFlow Project Summary

## Overview

This is a complete, production-ready reimplementation of the AgentFlow framework using Amazon Strands SDK and Amazon Bedrock with Claude Sonnet 4 and Haiku 4.5 models.

## What is AgentFlow?

AgentFlow is a framework for building structured agentic workflows that enable complex multi-step reasoning and task execution. Based on the research paper "AgentFlow: A Framework for Structured Agentic Workflows" (arXiv:2510.05592), this implementation provides:

- **Structured Workflows**: Define multi-step agent workflows with clear dependencies
- **Intelligent Routing**: Automatic model selection between Claude Sonnet 4 (complex) and Haiku 4.5 (simple)
- **Reasoning Patterns**: Built-in support for Chain-of-Thought, ReAct, Tree-of-Thought, and more
- **Production Ready**: Comprehensive error handling, logging, and fault tolerance

## Key Differences from Original

This implementation differs from the original AgentFlow in several important ways:

1. **Cloud-Native**: Built on Amazon Bedrock instead of direct API calls
2. **Managed AI**: Uses AWS-managed Claude models for reliability and scale
3. **Enterprise Ready**: Production-quality logging, monitoring, and error handling
4. **Framework Integration**: Uses Amazon Strands SDK for agent orchestration

## Project Structure

```
agentflow/
├── src/agentflow/              # Main package
│   ├── core/                   # Core workflow and agent logic
│   │   ├── workflow.py         # Workflow orchestration engine
│   │   └── agent.py            # Agent implementations
│   ├── models/                 # Model integrations
│   │   └── bedrock_client.py   # Amazon Bedrock client
│   ├── patterns/               # Reasoning patterns
│   │   └── reasoning.py        # CoT, ReAct, ToT, etc.
│   └── utils/                  # Utilities
│       ├── logging.py          # Structured logging
│       └── exceptions.py       # Custom exceptions
├── examples/                   # Working examples
│   ├── basic_workflow.py       # Simple workflow
│   ├── parallel_workflow.py    # Parallel execution
│   ├── reasoning_workflow.py   # Reasoning patterns
│   └── tool_agent_workflow.py  # Tool-calling agents
├── tests/                      # Comprehensive test suite
│   ├── test_workflow.py        # Workflow tests
│   └── test_bedrock_client.py  # Bedrock client tests
├── docs/                       # Complete documentation
│   ├── getting_started.md      # User guide
│   ├── architecture_design.md  # Architecture details
│   ├── operation_runbook.md    # Operations guide
│   └── api_reference.md        # API documentation
├── config/                     # Configuration files
│   └── example_config.yaml     # Example configuration
└── scripts/                    # Deployment scripts
    └── deploy.sh               # Automated deployment
```

## Core Components

### 1. Workflow Engine (`workflow.py`)

The workflow engine orchestrates multi-step agent execution with:

- **Dependency Resolution**: Automatically determines execution order
- **Parallel Execution**: Runs independent steps concurrently
- **Retry Logic**: Automatic retry with exponential backoff
- **State Management**: Tracks workflow and step status
- **Result Propagation**: Passes results between dependent steps

**Key Features:**
- Circular dependency detection
- Configurable retry attempts
- Timeout management
- Comprehensive execution history

### 2. Agent Framework (`agent.py`)

Three types of agents for different use cases:

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

### 3. Bedrock Client (`bedrock_client.py`)

Production-ready client for Amazon Bedrock:

- **Model Abstraction**: Unified interface for Claude models
- **Fault Tolerance**: Automatic retry with exponential backoff
- **Error Handling**: Comprehensive error classification
- **Streaming Support**: Optional streaming responses
- **Model Selection**: Automatic routing based on task complexity

**Supported Models:**
- Claude Sonnet 4: Complex reasoning, analysis, creative tasks
- Claude Haiku 4.5: Simple tasks, fast responses, cost-effective

### 4. Reasoning Patterns (`reasoning.py`)

Five built-in reasoning patterns:

1. **Chain-of-Thought (CoT)**: Step-by-step reasoning
2. **ReAct**: Reasoning + Acting with tools
3. **Tree-of-Thought (ToT)**: Multiple reasoning paths
4. **Reflection**: Self-critique and refinement
5. **Plan-and-Solve**: Planning before execution

### 5. Utilities

**Logging** (`logging.py`)
- Structured JSON logging
- CloudWatch Logs integration
- Context propagation
- Production-ready formatting

**Exceptions** (`exceptions.py`)
- Custom exception hierarchy
- Precise error handling
- Clear error messages

## Production Features

### Fault Tolerance

1. **Automatic Retries**: Configurable retry attempts with exponential backoff
2. **Error Recovery**: Graceful handling of transient failures
3. **Timeout Management**: Prevents hanging workflows
4. **Circuit Breaking**: Prevents cascading failures

### Logging and Observability

1. **Structured Logging**: JSON-formatted logs for easy parsing
2. **CloudWatch Integration**: Native AWS CloudWatch support
3. **Execution History**: Complete audit trail of workflow execution
4. **Metrics Support**: Built-in metrics collection

### Security

1. **IAM Integration**: Uses AWS IAM for authentication
2. **Credential Management**: No hardcoded credentials
3. **Input Validation**: Validates all user inputs
4. **Encryption**: TLS for all AWS API calls

### Performance

1. **Parallel Execution**: Concurrent execution of independent steps
2. **Model Selection**: Automatic routing to appropriate model
3. **Connection Pooling**: Efficient AWS API usage
4. **Caching Support**: Framework for result caching

## Documentation

### User Documentation

1. **README.md**: Project overview and quick start
2. **getting_started.md**: Comprehensive user guide
3. **api_reference.md**: Complete API documentation
4. **Examples**: Four working example workflows

### Technical Documentation

1. **architecture_design.md**: System architecture and design decisions
2. **operation_runbook.md**: Operations and troubleshooting guide
3. **CONTRIBUTING.md**: Contribution guidelines
4. **CHANGELOG.md**: Version history

## Testing

Comprehensive test suite with:

- **Unit Tests**: Core component testing
- **Integration Tests**: End-to-end workflow testing
- **Mock Support**: Mocked AWS services for testing
- **Coverage**: >80% code coverage target

Run tests:
```bash
make test          # Run all tests
make test-cov      # Run with coverage report
```

## Configuration

Multiple configuration methods:

1. **YAML Configuration**: `config/example_config.yaml`
2. **Environment Variables**: `.env` file
3. **Programmatic**: Direct configuration in code

## Deployment

### Quick Deployment

```bash
# Run automated deployment script
./scripts/deploy.sh
```

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure AWS
aws configure

# Run example
python examples/basic_workflow.py
```

## Usage Examples

### Basic Workflow

```python
from agentflow import Workflow, WorkflowConfig, AgentConfig
from agentflow.core.agent import SimpleAgent
from agentflow.models.bedrock_client import BedrockClient, ModelType

# Initialize
bedrock = BedrockClient(region_name="us-east-1")
workflow = Workflow(WorkflowConfig(name="my_workflow"))

# Create agent
agent = SimpleAgent(
    config=AgentConfig(name="agent", model_type=ModelType.HAIKU_4_5),
    bedrock_client=bedrock,
    prompt_template="Process: {input}"
)

# Add step and execute
workflow.add_step("step1", agent, {"input": "data"})
result = await workflow.execute()
```

### Parallel Execution

```python
# Add independent steps (run in parallel)
workflow.add_step("analyze_a", agent_a, {"data": "x"})
workflow.add_step("analyze_b", agent_b, {"data": "y"})

# Add dependent step (waits for both)
workflow.add_step(
    "synthesize",
    synthesis_agent,
    {},
    dependencies=["analyze_a", "analyze_b"]
)
```

### Reasoning Patterns

```python
from agentflow.patterns.reasoning import get_reasoning_pattern, ReasoningPatternType

agent = ReasoningAgent(
    config=AgentConfig(
        name="reasoner",
        reasoning_pattern=get_reasoning_pattern(ReasoningPatternType.CHAIN_OF_THOUGHT)
    ),
    bedrock_client=bedrock
)
```

## Requirements

- Python 3.10+
- AWS Account with Bedrock access
- Claude Sonnet 4 and Haiku 4.5 model access
- AWS CLI configured

## Cost Considerations

Model pricing (approximate):
- Claude Sonnet 4: Higher cost, complex reasoning
- Claude Haiku 4.5: Lower cost, simple tasks

Use `get_model_for_task()` for automatic cost optimization.

## Monitoring

### CloudWatch Metrics

- Workflow success/failure rate
- Step execution time
- Model invocation latency
- Token usage
- Error rates

### CloudWatch Logs

Structured JSON logs with:
- Workflow execution traces
- Agent invocations
- Error details
- Performance metrics

## Troubleshooting

Common issues and solutions documented in `docs/operation_runbook.md`:

1. Model access denied → Enable in Bedrock console
2. Throttling errors → Request quota increase
3. High latency → Enable parallel execution
4. Memory issues → Limit concurrent workflows

## Future Enhancements

Planned features:
- Streaming response support in workflows
- Checkpoint and resume for long workflows
- Multi-region failover
- Enhanced cost optimization
- Human-in-the-loop support
- A/B testing framework

## Support and Resources

- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory
- **Tests**: See `tests/` directory
- **Issues**: GitHub Issues
- **AWS Bedrock**: https://docs.aws.amazon.com/bedrock/
- **Strands SDK**: https://github.com/strands-agents/sdk-python

## License

MIT License - See LICENSE file

## Acknowledgments

Based on the AgentFlow paper (arXiv:2510.05592) and original implementation.
Reimplemented for Amazon Bedrock and Strands SDK with production-quality features.

## Quick Start Checklist

- [ ] Install Python 3.10+
- [ ] Configure AWS credentials
- [ ] Enable Bedrock model access
- [ ] Run `./scripts/deploy.sh`
- [ ] Try `python examples/basic_workflow.py`
- [ ] Read `docs/getting_started.md`

## Contact

For questions, issues, or contributions, please refer to CONTRIBUTING.md.

---

**Project Status**: Production Ready (v0.1.0)

**Last Updated**: 2024-01-15
