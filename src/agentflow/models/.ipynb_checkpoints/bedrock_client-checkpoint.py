"""
Amazon Bedrock client for model interactions
"""

import json
from typing import Any, Dict, Optional, List
from enum import Enum
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from agentflow.utils.logging import setup_logger
from agentflow.utils.exceptions import BedrockError, ModelInvocationError

logger = setup_logger(__name__)


class ModelType(Enum):
    """Supported Bedrock model types"""
    SONNET_4_5 = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    HAIKU_4_5 = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


class BedrockClient:
    """
    Client for interacting with Amazon Bedrock
    
    Provides a unified interface for invoking Claude models with
    fault tolerance, retry logic, and comprehensive logging.
    """
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        max_retries: int = 3,
        timeout: int = 300
    ):
        self.region_name = region_name
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Configure boto3 client with retries
        config = Config(
            region_name=region_name,
            retries={
                'max_attempts': max_retries,
                'mode': 'adaptive'
            },
            connect_timeout=timeout,
            read_timeout=timeout
        )
        
        try:
            self.client = boto3.client('bedrock-runtime', config=config)
            self.logger = logger.bind(region=region_name)
            self.logger.info("Bedrock client initialized")
        except Exception as e:
            self.logger = logger
            self.logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise BedrockError(f"Failed to initialize Bedrock client: {str(e)}") from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, ModelInvocationError)),
        reraise=True
    )
    async def invoke(
        self,
        model_type: ModelType,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
        stop_sequences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Invoke a Bedrock model
        
        Args:
            model_type: The model to invoke
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Tool definitions for function calling
            stop_sequences: Sequences that stop generation
            
        Returns:
            Model response dictionary
        """
        model_id = model_type.value
        
        self.logger.info(
            "Invoking Bedrock model",
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        try:
            # Prepare request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            if tools:
                request_body["tools"] = tools
            
            if stop_sequences:
                request_body["stop_sequences"] = stop_sequences
            
            # Invoke model
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            self.logger.info(
                "Model invocation successful",
                model=model_id,
                stop_reason=response_body.get("stop_reason"),
                input_tokens=response_body.get("usage", {}).get("input_tokens"),
                output_tokens=response_body.get("usage", {}).get("output_tokens")
            )
            
            return response_body
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            self.logger.error(
                "Bedrock client error",
                model=model_id,
                error_code=error_code,
                error_message=error_message,
                exc_info=True
            )
            
            raise ModelInvocationError(
                f"Bedrock invocation failed [{error_code}]: {error_message}"
            ) from e
            
        except Exception as e:
            self.logger.error(
                "Unexpected error during model invocation",
                model=model_id,
                error=str(e),
                exc_info=True
            )
            raise ModelInvocationError(f"Model invocation failed: {str(e)}") from e
    
    async def invoke_with_streaming(
        self,
        model_type: ModelType,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """
        Invoke model with streaming response
        
        Yields response chunks as they arrive.
        """
        model_id = model_type.value
        
        self.logger.info("Starting streaming invocation", model=model_id)
        
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_data = json.loads(chunk.get('bytes').decode())
                        yield chunk_data
            
            self.logger.info("Streaming invocation completed", model=model_id)
            
        except Exception as e:
            self.logger.error(
                "Streaming invocation failed",
                model=model_id,
                error=str(e),
                exc_info=True
            )
            raise ModelInvocationError(f"Streaming invocation failed: {str(e)}") from e
    
    def get_model_for_task(self, task_complexity: str) -> ModelType:
        """
        Select appropriate model based on task complexity
        
        Args:
            task_complexity: "simple" or "complex"
            
        Returns:
            Appropriate ModelType
        """
        if task_complexity.lower() == "simple":
            return ModelType.HAIKU_4_5
        else:
            return ModelType.SONNET_4_5
