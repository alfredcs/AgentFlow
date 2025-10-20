#!/bin/bash
# Deployment script for AgentFlow

set -e

echo "=== AgentFlow Deployment Script ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}✗ Python 3.10+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Check AWS CLI
echo "Checking AWS CLI..."
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI installed${NC}"

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials configured${NC}"

# Check Bedrock access
echo "Checking Bedrock access..."
AWS_REGION=${AWS_REGION:-us-east-1}
if ! aws bedrock list-foundation-models --region $AWS_REGION &> /dev/null; then
    echo -e "${YELLOW}⚠ Cannot access Bedrock. Check permissions.${NC}"
else
    echo -e "${GREEN}✓ Bedrock accessible${NC}"
fi

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null
pip install -e . > /dev/null
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run tests
echo "Running tests..."
if pytest tests/ -v --tb=short; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi

# Check code quality
echo "Checking code quality..."
if command -v ruff &> /dev/null; then
    if ruff check src/ tests/ --quiet; then
        echo -e "${GREEN}✓ Code quality checks passed${NC}"
    else
        echo -e "${YELLOW}⚠ Code quality issues found${NC}"
    fi
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please configure .env file with your settings${NC}"
fi

# Verify deployment
echo "Verifying deployment..."
if python3 -c "from agentflow import Workflow, BedrockClient; print('Import successful')"; then
    echo -e "${GREEN}✓ AgentFlow can be imported${NC}"
else
    echo -e "${RED}✗ Import failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Configure .env file with your AWS settings"
echo "2. Run example: python examples/basic_workflow.py"
echo "3. Check documentation in docs/"
echo ""
echo "To activate the environment in the future:"
echo "  source venv/bin/activate"
