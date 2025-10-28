# AgentFlow - implementation of multi-trun agentic workflow with Bedrock and MCP

AgentFlow introduces a trainable agentic system that optimizes planning directly within multi-turn workflows, addressing a fundamental limitation in current tool-augmented LLMs.  This solution demonstrates that small, strategically trained agentic systems can outperform much larger monolithic models by learning effective planning through outcome-driven reinforcement learning in realistic multi-turn environments.

A production-ready implementation of AgentFlow using Amazon Strands SDK and Amazon Bedrock, enabling structured agentic workflows with Qwen 3-32B, Claude Sonnet 4.5 and Haiku 4.5.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🎯 Overview

AgentFlow is a framework for building complex agentic workflows through structured reasoning patterns. Based on the research paper ["AgentFlow: A Framework for Structured Agentic Workflows"](https://arxiv.org/pdf/2510.05592), this implementation provides a production-ready solution using:

- **Amazon Strands SDK**: Agent orchestration framework
- **Amazon Bedrock**: Managed AI service with Claude and Qwen models
- **MCP**: Enable agents access tools via MCP protocol
- **Claude Sonnet 4.5**: Primary reasoning model for complex tasks
- **Claude Haiku 4.5**: Fast model for simple operations
- **Qwen 3-32B**: Open source and fine-tunable fast model for agentic reasoning.

## ✨ Key Features
        

- **🔄 Structured Workflows**: Define multi-step agent workflows with clear reasoning patterns
- **🎯 Smart Model Routing**: Automatic routing between Sonnet 4.5 (complex) and Haiku 4.5 (simple)
- **🛡️ Fault Tolerance**: Comprehensive error handling and retry mechanisms
- **📊 Production Logging**: Structured logging with CloudWatch integration
- **👁️ Observability**: Built-in metrics and execution tracing
- **🔒 Type Safety**: Full type hints and validation
- **⚡ Parallel Execution**: Run independent steps concurrently
- **🧠 Reasoning Patterns**: Chain-of-Thought, ReAct, Tree-of-Thought, and more

##  🥳 Novel Training Algorithm: Flow-GVPO
This project implements **Group Variance Policy Optimization (GVPO)** as a replacement for GRPO in the AgentFlow training pipeline. GVPO offers superior theoretical guarantees and empirical performance, particularly on complex reasoning tasks.    

Theoretical Improvements Over GRPO 
 
| Feature | GRPO | GVPO | 
|---------|------|------| 
| Convergence | No proof | Proven optimal |
| KL Handling | External penalty | Analytical integration |
| Stability | Importance sampling issues | More stable |
| Performance | Baseline | +40% on AIME 2024 |

**How it works:**

- Converts multi-turn RL into a sequence of single-turn policy updates
- Broadcasts a single trajectory-level outcome reward to every turn in the reasoning chain
- Uses group-normalized advantages to stabilize training
- Mathematically proven equivalence: maximizing global multi-turn objective = maximizing expected token-level local objectives

**Known Limitations:**                                                                                                                                                                   
                                                                                                                                                                                    
- 1. **Data Format**: Requires Parquet files with specific columns (question, answer, data_id) 
- 2. **Model Support**: Tested with Qwen3-32B; other models may need adaptation 
- 3. **Hardware**: Designed for multi-GPU training; single-GPU support limited
- 4. **Dependencies**: Requires verl framework (external dependency)
     
**Key insight:** Instead of trying to assign different rewards to different steps (brittle), give the same final outcome to all steps and let the model learn which actions contribute to success.

##  🎉 Architectural Innovation: In-the-Flow Optimization
- Unlike monolithic tool-integrated models that train a single policy for all actions, AgentFlow decomposes reasoning into 4 specialized modules:
- Action Planner (trainable via RL)
- Tool Executor (frozen)
- Execution Verifier (frozen)
- Solution Generator (frozen)
- Modules coordinate through an evolving memory that provides structured, deterministic state tracking

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd AgentFlow

# Run automated setup
./scripts/deploy.sh

# Or manual installation
pip install -r requirements.txt
pip install -e .
```

### Configure AWS

```bash
# Configure AWS credentials
aws configure

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### Run Your First Workflow

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
    agent = SimpleAgent(
        config=AgentConfig(
            name="greeter",
            model_type=ModelType.HAIKU_4_5
        ),
        bedrock_client=bedrock,
        prompt_template="Generate a friendly greeting for {name}"
    )
    
    # Add step and execute
    workflow.add_step("greet", agent, {"name": "World"})
    result = await workflow.execute()
    
    print(result['results']['greet'])

if __name__ == "__main__":
    asyncio.run(main())
```

Save as `hello.py` and run:
```bash
python hello.py
```

## 📁 Project Structure

```
agentflow/
├── src/agentflow/          # Main package
│   ├── core/               # Core workflow and agent logic
│   │   ├── workflow.py     # Workflow orchestration engine
│   │   └── agent.py        # Agent implementations
│   ├── models/             # Model integrations
│   │   └── bedrock_client.py  # Amazon Bedrock client
│   ├── patterns/           # Reasoning patterns
│   │   └── reasoning.py    # CoT, ReAct, ToT, etc.
│   └── utils/              # Utilities
│       ├── logging.py      # Structured logging
│       └── exceptions.py   # Custom exceptions
├── examples/               # Working examples
│   ├── basic_workflow.py
│   ├── parallel_workflow.py
│   ├── reasoning_workflow.py
│   └── tool_agent_workflow.py
│   ├── planner_workflow.py
│   ├── rexecutor_workflow.py
│   └── solver_bedrock.py
├── tests/                  # Comprehensive test suite
├── docs/                   # Complete documentation
│   ├── getting_started.md
│   ├── architecture_design.md
│   ├── operation_runbook.md
│   └── api_reference.md
├── config/                 # Configuration files
└── scripts/                # Deployment scripts
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting_started.md) | Complete user guide and tutorials |
| [Architecture Design](docs/architecture_design.md) | System architecture and design decisions |
| [Operation Runbook](docs/operation_runbook.md) | Deployment, monitoring, and troubleshooting |
| [API Reference](docs/api_reference.md) | Complete API documentation |
| [Quick Reference](QUICK_REFERENCE.md) | Cheat sheet for common tasks |
| [Project Summary](PROJECT_SUMMARY.md) | Comprehensive project overview |

## 🎓 Examples

Explore working examples in the `examples/` directory:

- **basic_workflow.py**: Simple sequential workflow
- **parallel_workflow.py**: Parallel execution with multiple agents
- **reasoning_workflow.py**: Different reasoning patterns (CoT, ReAct, etc.)
- **tool_agent_workflow.py**: Agents with tool-calling capabilities
- **planner_workflow.py**: Query analysis, multi-step planning, Memory management, result verification
- **executor_workflow.py**: Tool command generation, command parsing, ool execution with timeout protection
- **solver_bedrock.py**: Orchestrates the complete workflow:1. Query analysis 2. Multi-step planning and execution 3. Memory management 4. Result generation

Run any example:
```bash
python examples/basic_workflow.py
```
Run a complete agentic workflow:
```bash
python examples/solver_bedrock.py --prompt "<your question>" --model_type <[sonnet|haiku|qwen]>
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run linters
make lint

# Format code
make format
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file:
```bash
AWS_REGION=us-east-1
AWS_PROFILE=default
AGENTFLOW_LOG_LEVEL=INFO
AGENTFLOW_MAX_RETRIES=3
```

### YAML Configuration

See `config/example_config.yaml` for complete configuration options.

## 🛠️ Development

### Prerequisites

- Python 3.10+
- AWS Account with Bedrock access
- Claude Sonnet 4.5 and Haiku 4.5 model access enabled
- AWS CLI configured

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Verify installation
python scripts/verify_installation.py
```

## 🏗️ Architecture

AgentFlow uses a modular architecture:

1. **Workflow Engine**: Orchestrates multi-step execution with dependency resolution
2. **Agent Framework**: Three agent types (Simple, Tool, Reasoning)
3. **Bedrock Client**: Production-ready AWS Bedrock integration
4. **Reasoning Patterns**: Five built-in patterns for structured thinking
5. **Utilities**: Logging, error handling, and observability

See [Architecture Design](docs/architecture_design.md) for details.

## 🔐 Security

- Uses AWS IAM for authentication
- No hardcoded credentials
- Input validation on all user inputs
- TLS encryption for all AWS API calls
- Comprehensive error handling

## 📊 Monitoring

### CloudWatch Integration

- Structured JSON logs
- Execution traces
- Performance metrics
- Error tracking

### Key Metrics

- Workflow success/failure rate
- Step execution time
- Model invocation latency
- Token usage and costs
- Retry rates

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Model access denied | Enable in AWS Bedrock console |
| Throttling errors | Request quota increase |
| High latency | Enable parallel execution |
| Import errors | Run `pip install -r requirements.txt` |

See [Operation Runbook](docs/operation_runbook.md) for comprehensive troubleshooting.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linters
6. Submit a pull request

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Based on the AgentFlow paper:
- Paper: [arXiv:2510.05592](https://arxiv.org/pdf/2510.05592)
- Original Repository: [lupantech/AgentFlow](https://github.com/lupantech/AgentFlow)

Reimplemented for Amazon Bedrock and Strands SDK with production-quality features.

## 📞 Support

- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## 🗺️ Roadmap

- [ ] Streaming response support in workflows
- [ ] Checkpoint and resume for long workflows
- [ ] Multi-region failover
- [ ] Enhanced cost optimization
- [ ] Human-in-the-loop support
- [ ] A/B testing framework
- [ ] Batch processing support

## 📈 Version

Current Version: **0.1.0** (Production Ready)

See [CHANGELOG.md](CHANGELOG.md) for version history.

## 🔗 Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Strands SDK](https://github.com/strands-agents/sdk-python)
- [Claude Model Documentation](https://docs.anthropic.com/claude/docs)
- [AgentFlow Paper](https://arxiv.org/pdf/2510.05592)

---
