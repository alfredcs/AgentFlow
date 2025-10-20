# AgentFlow Setup Checklist

Use this checklist to ensure your AgentFlow installation is complete and ready for production use.

## Pre-Installation

### System Requirements
- [ ] Python 3.10 or higher installed
- [ ] pip package manager available
- [ ] Virtual environment support (venv)
- [ ] Git installed (for cloning repository)

### AWS Requirements
- [ ] AWS Account created
- [ ] AWS CLI installed
- [ ] AWS credentials configured (`aws configure`)
- [ ] Access to us-east-1 region (or your preferred region)

### Bedrock Requirements
- [ ] Amazon Bedrock service available in your region
- [ ] Model access requested for Claude Sonnet 4
- [ ] Model access requested for Claude Haiku 4.5
- [ ] Model access approved (usually instant)

## Installation Steps

### 1. Repository Setup
- [ ] Repository cloned or downloaded
- [ ] Changed to project directory
- [ ] Reviewed README.md

### 2. Python Environment
- [ ] Virtual environment created (`python3 -m venv venv`)
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] pip upgraded (`pip install --upgrade pip`)

### 3. Dependencies
- [ ] Requirements file reviewed (`requirements.txt`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] AgentFlow package installed (`pip install -e .`)
- [ ] No installation errors

### 4. AWS Configuration
- [ ] AWS credentials configured
- [ ] AWS region set (default: us-east-1)
- [ ] AWS profile configured (if using multiple profiles)
- [ ] Credentials verified (`aws sts get-caller-identity`)

### 5. Bedrock Access
- [ ] Bedrock service accessible (`aws bedrock list-foundation-models`)
- [ ] Claude Sonnet 4 model listed
- [ ] Claude Haiku 4.5 model listed
- [ ] Test invocation successful

### 6. Environment Configuration
- [ ] `.env.example` copied to `.env`
- [ ] AWS_REGION set in `.env`
- [ ] AWS_PROFILE set in `.env` (if needed)
- [ ] Log level configured
- [ ] Other settings customized

## Verification

### Import Tests
- [ ] Can import agentflow (`python -c "import agentflow"`)
- [ ] Can import Workflow (`from agentflow import Workflow`)
- [ ] Can import BedrockClient (`from agentflow.models.bedrock_client import BedrockClient`)
- [ ] No import errors

### Functionality Tests
- [ ] Run verification script (`python scripts/verify_installation.py`)
- [ ] All checks passed
- [ ] Run basic example (`python examples/basic_workflow.py`)
- [ ] Example executed successfully
- [ ] Results displayed correctly

### Unit Tests
- [ ] Test suite runs (`make test` or `pytest tests/`)
- [ ] All tests pass
- [ ] No test failures or errors

### Code Quality
- [ ] Linters run successfully (`make lint`)
- [ ] Code formatted (`make format`)
- [ ] No linting errors

## Documentation Review

### Essential Documentation
- [ ] Read README.md
- [ ] Read Getting Started guide (`docs/getting_started.md`)
- [ ] Reviewed Quick Reference (`QUICK_REFERENCE.md`)
- [ ] Understand project structure

### Technical Documentation
- [ ] Reviewed Architecture Design (`docs/architecture_design.md`)
- [ ] Reviewed API Reference (`docs/api_reference.md`)
- [ ] Understand workflow concepts
- [ ] Understand agent types

### Operational Documentation
- [ ] Reviewed Operation Runbook (`docs/operation_runbook.md`)
- [ ] Understand monitoring setup
- [ ] Understand troubleshooting procedures
- [ ] Know where to find help

## Configuration

### Workflow Configuration
- [ ] Understand WorkflowConfig options
- [ ] Know how to set max_retries
- [ ] Know how to enable parallel execution
- [ ] Understand timeout settings

### Agent Configuration
- [ ] Understand AgentConfig options
- [ ] Know how to select models
- [ ] Understand temperature settings
- [ ] Know how to set max_tokens

### Logging Configuration
- [ ] Understand log levels
- [ ] Know how to enable CloudWatch
- [ ] Understand structured logging
- [ ] Can access logs

## Security

### IAM Permissions
- [ ] IAM policy created for Bedrock access
- [ ] IAM policy attached to user/role
- [ ] Permissions tested
- [ ] Least privilege principle applied

### Credentials Management
- [ ] No hardcoded credentials in code
- [ ] Using IAM roles (if on EC2/ECS/Lambda)
- [ ] Using AWS profiles (if local development)
- [ ] Credentials not committed to git

### Network Security
- [ ] Understand TLS encryption for API calls
- [ ] Know VPC requirements (if applicable)
- [ ] Understand security groups (if applicable)

## Monitoring Setup

### CloudWatch Logs
- [ ] Log group created (if needed)
- [ ] Log streams working
- [ ] Can view logs in CloudWatch console
- [ ] Log retention configured

### CloudWatch Metrics
- [ ] Understand available metrics
- [ ] Know how to view metrics
- [ ] Alerts configured (optional)
- [ ] Dashboard created (optional)

### Application Monitoring
- [ ] Understand execution history
- [ ] Know how to track workflow status
- [ ] Can monitor token usage
- [ ] Can track costs

## Production Readiness

### Error Handling
- [ ] Understand retry logic
- [ ] Know how to handle WorkflowError
- [ ] Know how to handle AgentExecutionError
- [ ] Understand error recovery

### Performance
- [ ] Understand parallel execution
- [ ] Know when to use Haiku vs Sonnet
- [ ] Understand timeout settings
- [ ] Know how to optimize prompts

### Scalability
- [ ] Understand concurrent workflow limits
- [ ] Know Bedrock quotas
- [ ] Understand rate limiting
- [ ] Know how to request quota increases

### Reliability
- [ ] Understand fault tolerance features
- [ ] Know retry mechanisms
- [ ] Understand circuit breaking
- [ ] Have backup plans

## Development Workflow

### Version Control
- [ ] Git repository initialized (if needed)
- [ ] .gitignore configured
- [ ] Initial commit made
- [ ] Remote repository configured (if needed)

### Development Tools
- [ ] IDE/editor configured
- [ ] Linters integrated
- [ ] Formatters integrated
- [ ] Debugger configured

### Testing Strategy
- [ ] Understand test structure
- [ ] Know how to run tests
- [ ] Know how to add tests
- [ ] Understand mocking

### CI/CD (Optional)
- [ ] CI pipeline configured
- [ ] Automated tests running
- [ ] Deployment pipeline configured
- [ ] Monitoring integrated

## Team Onboarding

### Documentation
- [ ] Team has access to documentation
- [ ] Getting Started guide shared
- [ ] Quick Reference distributed
- [ ] Examples demonstrated

### Training
- [ ] Team understands AgentFlow concepts
- [ ] Team knows how to create workflows
- [ ] Team understands agent types
- [ ] Team knows troubleshooting procedures

### Support
- [ ] Support channels established
- [ ] Issue tracking configured
- [ ] Communication channels set up
- [ ] Escalation path defined

## Post-Installation

### Validation
- [ ] Run all examples successfully
- [ ] Create a custom workflow
- [ ] Test error handling
- [ ] Verify monitoring

### Optimization
- [ ] Review configuration settings
- [ ] Optimize for your use case
- [ ] Configure cost controls
- [ ] Set up alerts

### Maintenance
- [ ] Schedule for updates
- [ ] Plan for dependency updates
- [ ] Set up backup procedures
- [ ] Document custom configurations

## Troubleshooting Checklist

If you encounter issues, verify:

- [ ] Python version is 3.10+
- [ ] All dependencies installed
- [ ] AWS credentials configured
- [ ] Bedrock access enabled
- [ ] Models accessible
- [ ] Network connectivity
- [ ] IAM permissions correct
- [ ] No firewall blocking AWS APIs
- [ ] Logs showing detailed errors
- [ ] Reviewed Operation Runbook

## Getting Help

If you need assistance:

1. [ ] Check documentation in `docs/` directory
2. [ ] Review examples in `examples/` directory
3. [ ] Search existing GitHub issues
4. [ ] Check Operation Runbook troubleshooting section
5. [ ] Create new GitHub issue with details
6. [ ] Include error messages and logs
7. [ ] Provide system information

## Sign-Off

Installation completed by: ________________

Date: ________________

Verified by: ________________

Date: ________________

Notes:
_____________________________________________
_____________________________________________
_____________________________________________

---

## Quick Commands Reference

```bash
# Verify installation
python scripts/verify_installation.py

# Run tests
make test

# Run example
python examples/basic_workflow.py

# Check AWS access
aws sts get-caller-identity

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1

# View logs (if using CloudWatch)
aws logs tail /aws/agentflow/production --follow
```

---

**Status**: [ ] Setup Complete [ ] Pending [ ] Issues Found

**Ready for Production**: [ ] Yes [ ] No [ ] Needs Review
