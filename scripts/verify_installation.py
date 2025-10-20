#!/usr/bin/env python3
"""
Verification script for AgentFlow installation
"""

import sys
import subprocess
from typing import Tuple


def check_python_version() -> Tuple[bool, str]:
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        return True, f"✓ Python {version.major}.{version.minor}.{version.micro}"
    return False, f"✗ Python {version.major}.{version.minor} (3.10+ required)"


def check_import(module_name: str) -> Tuple[bool, str]:
    """Check if module can be imported"""
    try:
        __import__(module_name)
        return True, f"✓ {module_name} installed"
    except ImportError:
        return False, f"✗ {module_name} not found"


def check_aws_cli() -> Tuple[bool, str]:
    """Check AWS CLI"""
    try:
        result = subprocess.run(
            ["aws", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split()[0]
            return True, f"✓ AWS CLI installed ({version})"
        return False, "✗ AWS CLI not working"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "✗ AWS CLI not found"


def check_aws_credentials() -> Tuple[bool, str]:
    """Check AWS credentials"""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "✓ AWS credentials configured"
        return False, "✗ AWS credentials not configured"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "✗ Cannot verify AWS credentials"


def check_bedrock_access() -> Tuple[bool, str]:
    """Check Bedrock access"""
    try:
        result = subprocess.run(
            ["aws", "bedrock", "list-foundation-models", "--region", "us-east-1"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "✓ Bedrock accessible"
        return False, "✗ Bedrock not accessible"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "✗ Cannot verify Bedrock access"


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("AgentFlow Installation Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("boto3", lambda: check_import("boto3")),
        ("pydantic", lambda: check_import("pydantic")),
        ("structlog", lambda: check_import("structlog")),
        ("tenacity", lambda: check_import("tenacity")),
        ("AgentFlow", lambda: check_import("agentflow")),
        ("AWS CLI", check_aws_cli),
        ("AWS Credentials", check_aws_credentials),
        ("Bedrock Access", check_bedrock_access),
    ]
    
    results = []
    for name, check_func in checks:
        success, message = check_func()
        results.append((success, message))
        print(f"{message}")
    
    print()
    print("=" * 60)
    
    passed = sum(1 for success, _ in results if success)
    total = len(results)
    
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print()
        print("✓ All checks passed! AgentFlow is ready to use.")
        print()
        print("Next steps:")
        print("  1. Run example: python examples/basic_workflow.py")
        print("  2. Read docs: docs/getting_started.md")
        return 0
    else:
        print()
        print("⚠ Some checks failed. Please address the issues above.")
        print()
        print("Common fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Configure AWS: aws configure")
        print("  - Enable Bedrock: AWS Console → Bedrock → Model access")
        return 1


if __name__ == "__main__":
    sys.exit(main())
