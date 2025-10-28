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
    QWEN_3_32B = "qwen.qwen3-32b-v1:0"


class BedrockClient:
    """
    Client for interacting with Amazon Bedrock

    Provides a unified interface for invoking multiple model types including
    Claude (Sonnet 4.5, Haiku 4.5) and Qwen (3-32B) with fault tolerance,
    retry logic, and comprehensive logging.

    All responses are normalized to a consistent format regardless of the
    underlying model, ensuring downstream processes work without modification.
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

    def _is_claude_model(self, model_type: ModelType) -> bool:
        """Check if the model is a Claude model"""
        return model_type in [ModelType.SONNET_4_5, ModelType.HAIKU_4_5]

    def _prepare_request_body(
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
        Prepare request body based on model type

        Both Claude and Qwen models use the messages format.
        The main difference is in the version field and some optional parameters.
        """
        if self._is_claude_model(model_type):
            # Claude format with Anthropic version
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
        else:
            # Qwen format - also uses messages but without anthropic_version
            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            # Add user message
            messages.append({
                "role": "user",
                "content": prompt
            })

            request_body = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            if stop_sequences:
                request_body["stop"] = stop_sequences

        return request_body

    def _normalize_response(
        self,
        model_type: ModelType,
        response_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize response to Claude-like format for consistency

        This ensures downstream processes receive the same format
        regardless of which model was used.
        """
        if self._is_claude_model(model_type):
            # Claude response is already in the desired format
            return response_body
        else:
            # Qwen response - normalize to Claude format
            # Qwen uses messages API, so response format is similar to Claude
            # but may have slightly different field names or structure

            # Check if response already has the expected format
            if "content" in response_body and isinstance(response_body["content"], list):
                # Response is already in the correct format
                return response_body

            # Otherwise, try to normalize from various possible formats
            content_text = ""
            stop_reason = "end_turn"
            usage_info = {"input_tokens": 0, "output_tokens": 0}

            # Try different possible response formats

            # Format 1: {"choices": [{"message": {"content": "..."}}]}
            if "choices" in response_body and isinstance(response_body["choices"], list):
                if response_body["choices"]:
                    choice = response_body["choices"][0]
                    if "message" in choice:
                        content_text = choice["message"].get("content", "")
                    elif "text" in choice:
                        content_text = choice["text"]
                    # Get stop reason from choices
                    stop_reason = choice.get("finish_reason", choice.get("stop_reason", "end_turn"))

            # Format 2: {"output": {"text": "..."}} or {"output": "..."}
            elif "output" in response_body:
                if isinstance(response_body["output"], str):
                    content_text = response_body["output"]
                elif isinstance(response_body["output"], dict):
                    # Check nested structures
                    if "text" in response_body["output"]:
                        content_text = response_body["output"]["text"]
                    elif "message" in response_body["output"]:
                        if isinstance(response_body["output"]["message"], dict):
                            content_text = response_body["output"]["message"].get("content", "")
                        else:
                            content_text = str(response_body["output"]["message"])
                    elif "choices" in response_body["output"]:
                        choices = response_body["output"]["choices"]
                        if choices and isinstance(choices, list):
                            content_text = choices[0].get("message", {}).get("content", "")

            # Format 3: {"generated_text": "..."}
            elif "generated_text" in response_body:
                content_text = response_body["generated_text"]

            # Format 4: {"completion": "..."}
            elif "completion" in response_body:
                content_text = response_body["completion"]

            # Format 5: {"message": {"content": "..."}}
            elif "message" in response_body:
                if isinstance(response_body["message"], dict):
                    content_text = response_body["message"].get("content", "")
                else:
                    content_text = str(response_body["message"])

            # Format 6: {"text": "..."}
            elif "text" in response_body:
                content_text = response_body["text"]

            # Extract usage information
            if "usage" in response_body and isinstance(response_body["usage"], dict):
                usage_info = {
                    "input_tokens": response_body["usage"].get("prompt_tokens", response_body["usage"].get("input_tokens", 0)),
                    "output_tokens": response_body["usage"].get("completion_tokens", response_body["usage"].get("output_tokens", 0))
                }
            else:
                # Try direct fields
                usage_info = {
                    "input_tokens": response_body.get("prompt_tokens", response_body.get("input_tokens", 0)),
                    "output_tokens": response_body.get("completion_tokens", response_body.get("output_tokens", 0))
                }

            # Get stop reason if not already set
            if stop_reason == "end_turn":
                stop_reason = response_body.get("stop_reason", response_body.get("finish_reason", "end_turn"))

            # Construct normalized response
            normalized = {
                "content": [
                    {
                        "type": "text",
                        "text": content_text
                    }
                ],
                "stop_reason": stop_reason,
                "usage": usage_info
            }

            # Log if content is empty for debugging
            if not content_text:
                self.logger.warning(
                    "Empty content after normalization",
                    model_type=model_type.name,
                    response_keys=list(response_body.keys())
                )

            return normalized

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

        Supports Claude (Sonnet 4.5, Haiku 4.5) and Qwen (3-32B) models.
        Responses are automatically normalized to a consistent format.

        Args:
            model_type: The model to invoke (SONNET_4_5, HAIKU_4_5, or QWEN_3_32B)
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Tool definitions for function calling (Claude models only)
            stop_sequences: Sequences that stop generation

        Returns:
            Model response dictionary in normalized Claude-compatible format
        """
        model_id = model_type.value
        
        self.logger.info(
            "Invoking Bedrock model",
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens
        )

        try:
            # Prepare request body based on model type
            request_body = self._prepare_request_body(
                model_type=model_type,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                stop_sequences=stop_sequences
            )

            # Invoke model
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Log raw response for debugging (especially for non-Claude models)
            if not self._is_claude_model(model_type):
                self.logger.debug(
                    f"Raw {model_type.name} response",
                    response_preview=str(response_body)[:500]
                )
                # Also print to console for easier debugging
                print(f"\n=== RAW {model_type.name} RESPONSE ===")
                print(json.dumps(response_body, indent=2))
                print("=" * 50 + "\n")

            # Normalize response to ensure consistent format
            normalized_response = self._normalize_response(model_type, response_body)

            self.logger.info(
                "Model invocation successful",
                model=model_id,
                stop_reason=normalized_response.get("stop_reason"),
                input_tokens=normalized_response.get("usage", {}).get("input_tokens"),
                output_tokens=normalized_response.get("usage", {}).get("output_tokens")
            )

            return normalized_response
            
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
        Note: Response chunks are normalized to Claude format for consistency.
        """
        model_id = model_type.value

        self.logger.info("Starting streaming invocation", model=model_id)

        try:
            # Prepare request body based on model type
            request_body = self._prepare_request_body(
                model_type=model_type,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=None,
                stop_sequences=None
            )

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
                        # For Qwen models, normalize streaming chunks to Claude format
                        if not self._is_claude_model(model_type):
                            # Qwen streaming chunk format may differ
                            # Check if already in Claude format
                            if 'type' in chunk_data and 'delta' in chunk_data:
                                # Already in Claude-like format
                                yield chunk_data
                            elif 'token' in chunk_data or 'text' in chunk_data:
                                # Normalize to Claude-like streaming format
                                normalized_chunk = {
                                    "type": "content_block_delta",
                                    "delta": {
                                        "type": "text_delta",
                                        "text": chunk_data.get('token', chunk_data.get('text', ''))
                                    }
                                }
                                yield normalized_chunk
                            else:
                                # Pass through as-is
                                yield chunk_data
                        else:
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
