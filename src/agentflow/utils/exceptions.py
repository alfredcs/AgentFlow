"""
Custom exceptions for AgentFlow
"""


class AgentFlowError(Exception):
    """Base exception for AgentFlow"""
    pass


class WorkflowError(AgentFlowError):
    """Workflow execution errors"""
    pass


class AgentExecutionError(AgentFlowError):
    """Agent execution errors"""
    pass


class BedrockError(AgentFlowError):
    """Bedrock client errors"""
    pass


class ModelInvocationError(BedrockError):
    """Model invocation errors"""
    pass


class ConfigurationError(AgentFlowError):
    """Configuration errors"""
    pass


class ValidationError(AgentFlowError):
    """Input validation errors"""
    pass
