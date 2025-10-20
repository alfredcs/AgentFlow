# Contributing to AgentFlow

Thank you for your interest in contributing to AgentFlow! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/agentflow.git
cd agentflow
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 3. Configure AWS

```bash
aws configure
# Ensure Bedrock access is enabled
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write clean, documented code
- Follow existing code style
- Add tests for new functionality
- Update documentation

### 3. Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run linters
make lint
```

### 4. Format Code

```bash
make format
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

Use conventional commit messages:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:
- Clear description of changes
- Link to related issues
- Test results
- Documentation updates

## Code Style

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use descriptive variable names

### Documentation

- Add docstrings to all public functions/classes
- Update README.md for user-facing changes
- Add examples for new features

### Testing

- Write unit tests for new code
- Maintain >80% code coverage
- Test edge cases and error conditions

## Project Structure

```
agentflow/
├── src/agentflow/       # Main package
│   ├── core/            # Core workflow and agent logic
│   ├── models/          # Bedrock client
│   ├── patterns/        # Reasoning patterns
│   └── utils/           # Utilities
├── tests/               # Test suite
├── examples/            # Example workflows
├── docs/                # Documentation
└── config/              # Configuration files
```

## Adding New Features

### New Agent Type

1. Create class in `src/agentflow/core/agent.py`
2. Extend `Agent` base class
3. Implement `_prepare_prompt` and `_process_response`
4. Add tests in `tests/test_agent.py`
5. Add example in `examples/`
6. Update documentation

### New Reasoning Pattern

1. Create class in `src/agentflow/patterns/reasoning.py`
2. Extend `ReasoningPattern` base class
3. Implement `apply` method
4. Add to `ReasoningPatternType` enum
5. Update `get_reasoning_pattern` factory
6. Add tests and examples

### New Model Support

1. Add model to `ModelType` enum in `bedrock_client.py`
2. Update model selection logic
3. Add tests
4. Update documentation

## Testing Guidelines

### Unit Tests

```python
import pytest
from agentflow import Workflow, WorkflowConfig

def test_workflow_creation():
    """Test workflow can be created"""
    workflow = Workflow(WorkflowConfig(name="test"))
    assert workflow.config.name == "test"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_workflow_execution(mock_bedrock):
    """Test full workflow execution"""
    workflow = create_test_workflow()
    result = await workflow.execute()
    assert result["status"] == "completed"
```

### Mocking

Use mocks for external services:

```python
from unittest.mock import Mock, AsyncMock

mock_bedrock = Mock(spec=BedrockClient)
mock_bedrock.invoke = AsyncMock(return_value={"content": [{"text": "response"}]})
```

## Documentation

### Docstring Format

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When validation fails
    """
    pass
```

### README Updates

Update README.md for:
- New features
- API changes
- Installation changes
- Configuration changes

### Documentation Files

Update relevant docs:
- `docs/getting_started.md`: User guide
- `docs/architecture_design.md`: Architecture changes
- `docs/operation_runbook.md`: Operational procedures
- `docs/api_reference.md`: API documentation

## Review Process

### Before Submitting PR

- [ ] All tests pass
- [ ] Code is formatted
- [ ] Documentation is updated
- [ ] Examples work
- [ ] No linting errors

### PR Review

Maintainers will review for:
- Code quality
- Test coverage
- Documentation
- Performance impact
- Security considerations

### After Approval

- Squash commits if needed
- Merge to main branch
- Update changelog

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish package

## Getting Help

- Open an issue for bugs
- Start a discussion for questions
- Join our community chat

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to AgentFlow!
