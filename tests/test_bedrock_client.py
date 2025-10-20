"""
Tests for Bedrock client
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.utils.exceptions import BedrockError, ModelInvocationError


@pytest.fixture
def mock_boto_client():
    """Mock boto3 Bedrock client"""
    with patch('boto3.client') as mock_client:
        client = MagicMock()
        mock_client.return_value = client
        yield client


class TestBedrockClient:
    """Test Bedrock client functionality"""
    
    def test_client_initialization(self, mock_boto_client):
        """Test client can be initialized"""
        client = BedrockClient(region_name="us-east-1")
        
        assert client.region_name == "us-east-1"
        assert client.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_invoke_success(self, mock_boto_client):
        """Test successful model invocation"""
        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        response_body = {
            'content': [{'text': 'Test response'}],
            'usage': {'input_tokens': 10, 'output_tokens': 20},
            'stop_reason': 'end_turn'
        }
        
        mock_response['body'].read.return_value = json.dumps(response_body).encode()
        mock_boto_client.invoke_model.return_value = mock_response
        
        client = BedrockClient()
        result = await client.invoke(
            model_type=ModelType.HAIKU_4_5,
            prompt="Test prompt"
        )
        
        assert result['content'][0]['text'] == 'Test response'
        assert result['usage']['input_tokens'] == 10
    
    @pytest.mark.asyncio
    async def test_invoke_with_system_prompt(self, mock_boto_client):
        """Test invocation with system prompt"""
        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        response_body = {
            'content': [{'text': 'Response'}],
            'usage': {'input_tokens': 15, 'output_tokens': 25}
        }
        
        mock_response['body'].read.return_value = json.dumps(response_body).encode()
        mock_boto_client.invoke_model.return_value = mock_response
        
        client = BedrockClient()
        await client.invoke(
            model_type=ModelType.SONNET_4,
            prompt="Test",
            system_prompt="You are a helpful assistant"
        )
        
        call_args = mock_boto_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        
        assert 'system' in body
        assert body['system'] == "You are a helpful assistant"
    
    @pytest.mark.asyncio
    async def test_invoke_with_tools(self, mock_boto_client):
        """Test invocation with tools"""
        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        response_body = {
            'content': [{'type': 'tool_use', 'name': 'calculator'}],
            'usage': {'input_tokens': 20, 'output_tokens': 30}
        }
        
        mock_response['body'].read.return_value = json.dumps(response_body).encode()
        mock_boto_client.invoke_model.return_value = mock_response
        
        tools = [
            {
                'name': 'calculator',
                'description': 'Perform calculations',
                'input_schema': {'type': 'object'}
            }
        ]
        
        client = BedrockClient()
        result = await client.invoke(
            model_type=ModelType.SONNET_4,
            prompt="Calculate 2+2",
            tools=tools
        )
        
        assert result['content'][0]['type'] == 'tool_use'
    
    @pytest.mark.asyncio
    async def test_invoke_client_error(self, mock_boto_client):
        """Test handling of client errors"""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        
        mock_boto_client.invoke_model.side_effect = ClientError(
            error_response,
            'InvokeModel'
        )
        
        client = BedrockClient()
        
        with pytest.raises(ModelInvocationError, match="Access denied"):
            await client.invoke(
                model_type=ModelType.HAIKU_4_5,
                prompt="Test"
            )
    
    @pytest.mark.asyncio
    async def test_invoke_throttling_error(self, mock_boto_client):
        """Test handling of throttling errors"""
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            }
        }
        
        mock_boto_client.invoke_model.side_effect = ClientError(
            error_response,
            'InvokeModel'
        )
        
        client = BedrockClient()
        
        with pytest.raises(ModelInvocationError, match="Rate exceeded"):
            await client.invoke(
                model_type=ModelType.SONNET_4,
                prompt="Test"
            )
    
    def test_get_model_for_task(self):
        """Test model selection based on task complexity"""
        client = BedrockClient()
        
        simple_model = client.get_model_for_task("simple")
        assert simple_model == ModelType.HAIKU_4_5
        
        complex_model = client.get_model_for_task("complex")
        assert complex_model == ModelType.SONNET_4
    
    @pytest.mark.asyncio
    async def test_invoke_with_temperature(self, mock_boto_client):
        """Test invocation with custom temperature"""
        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        response_body = {
            'content': [{'text': 'Response'}],
            'usage': {'input_tokens': 10, 'output_tokens': 20}
        }
        
        mock_response['body'].read.return_value = json.dumps(response_body).encode()
        mock_boto_client.invoke_model.return_value = mock_response
        
        client = BedrockClient()
        await client.invoke(
            model_type=ModelType.HAIKU_4_5,
            prompt="Test",
            temperature=0.9
        )
        
        call_args = mock_boto_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        
        assert body['temperature'] == 0.9
