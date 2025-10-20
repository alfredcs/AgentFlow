"""
Tests for workflow engine
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from agentflow.core.workflow import Workflow, WorkflowConfig, WorkflowStatus
from agentflow.core.agent import Agent, AgentConfig
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.utils.exceptions import WorkflowError, AgentExecutionError


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client"""
    client = Mock(spec=BedrockClient)
    client.invoke = AsyncMock(return_value={
        "content": [{"text": "test response"}],
        "usage": {"input_tokens": 10, "output_tokens": 20}
    })
    return client


@pytest.fixture
def mock_agent(mock_bedrock_client):
    """Mock agent"""
    agent = Mock(spec=Agent)
    agent.config = AgentConfig(name="test_agent", model_type=ModelType.HAIKU_4_5)
    agent.execute = AsyncMock(return_value="test result")
    return agent


class TestWorkflow:
    """Test workflow functionality"""
    
    def test_workflow_creation(self):
        """Test workflow can be created"""
        config = WorkflowConfig(name="test_workflow")
        workflow = Workflow(config)
        
        assert workflow.config.name == "test_workflow"
        assert workflow.status == WorkflowStatus.PENDING
        assert len(workflow.steps) == 0
    
    def test_add_step(self, mock_agent):
        """Test adding steps to workflow"""
        workflow = Workflow(WorkflowConfig(name="test"))
        
        workflow.add_step("step1", mock_agent, {"input": "data"})
        
        assert "step1" in workflow.steps
        assert workflow.steps["step1"].agent == mock_agent
    
    def test_add_duplicate_step_raises_error(self, mock_agent):
        """Test adding duplicate step raises error"""
        workflow = Workflow(WorkflowConfig(name="test"))
        workflow.add_step("step1", mock_agent, {})
        
        with pytest.raises(WorkflowError, match="already exists"):
            workflow.add_step("step1", mock_agent, {})
    
    @pytest.mark.asyncio
    async def test_execute_single_step(self, mock_agent):
        """Test executing workflow with single step"""
        workflow = Workflow(WorkflowConfig(name="test"))
        workflow.add_step("step1", mock_agent, {"input": "data"})
        
        result = await workflow.execute()
        
        assert result["status"] == "completed"
        assert "step1" in result["results"]
        mock_agent.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_sequential_steps(self, mock_agent):
        """Test executing sequential steps"""
        workflow = Workflow(WorkflowConfig(name="test"))
        
        agent1 = Mock(spec=Agent)
        agent1.config = AgentConfig(name="agent1")
        agent1.execute = AsyncMock(return_value="result1")
        
        agent2 = Mock(spec=Agent)
        agent2.config = AgentConfig(name="agent2")
        agent2.execute = AsyncMock(return_value="result2")
        
        workflow.add_step("step1", agent1, {})
        workflow.add_step("step2", agent2, {}, dependencies=["step1"])
        
        result = await workflow.execute()
        
        assert result["status"] == "completed"
        assert result["results"]["step1"] == "result1"
        assert result["results"]["step2"] == "result2"
    
    @pytest.mark.asyncio
    async def test_execute_parallel_steps(self, mock_agent):
        """Test executing parallel steps"""
        workflow = Workflow(WorkflowConfig(name="test", enable_parallel=True))
        
        agent1 = Mock(spec=Agent)
        agent1.config = AgentConfig(name="agent1")
        agent1.execute = AsyncMock(return_value="result1")
        
        agent2 = Mock(spec=Agent)
        agent2.config = AgentConfig(name="agent2")
        agent2.execute = AsyncMock(return_value="result2")
        
        workflow.add_step("step1", agent1, {})
        workflow.add_step("step2", agent2, {})
        
        result = await workflow.execute()
        
        assert result["status"] == "completed"
        assert len(result["results"]) == 2
    
    def test_validate_circular_dependency(self, mock_agent):
        """Test detection of circular dependencies"""
        workflow = Workflow(WorkflowConfig(name="test"))
        
        workflow.add_step("step1", mock_agent, {}, dependencies=["step2"])
        workflow.add_step("step2", mock_agent, {}, dependencies=["step1"])
        
        with pytest.raises(WorkflowError, match="Circular dependency"):
            workflow._validate_workflow()
    
    def test_validate_missing_dependency(self, mock_agent):
        """Test detection of missing dependencies"""
        workflow = Workflow(WorkflowConfig(name="test"))
        
        workflow.add_step("step1", mock_agent, {}, dependencies=["nonexistent"])
        
        with pytest.raises(WorkflowError, match="non-existent"):
            workflow._validate_workflow()
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, mock_agent):
        """Test retry logic on step failure"""
        workflow = Workflow(WorkflowConfig(name="test", max_retries=2))
        
        agent = Mock(spec=Agent)
        agent.config = AgentConfig(name="failing_agent")
        agent.execute = AsyncMock(side_effect=[
            Exception("First failure"),
            Exception("Second failure"),
            "success"
        ])
        
        workflow.add_step("step1", agent, {})
        
        result = await workflow.execute()
        
        assert result["status"] == "completed"
        assert agent.execute.call_count == 3
    
    @pytest.mark.asyncio
    async def test_workflow_fails_after_max_retries(self, mock_agent):
        """Test workflow fails after exhausting retries"""
        workflow = Workflow(WorkflowConfig(name="test", max_retries=1))
        
        agent = Mock(spec=Agent)
        agent.config = AgentConfig(name="failing_agent")
        agent.execute = AsyncMock(side_effect=Exception("Persistent failure"))
        
        workflow.add_step("step1", agent, {})
        
        with pytest.raises(WorkflowError):
            await workflow.execute()
    
    def test_resolve_dependencies(self, mock_agent):
        """Test dependency resolution"""
        workflow = Workflow(WorkflowConfig(name="test"))
        
        workflow.add_step("step1", mock_agent, {})
        workflow.add_step("step2", mock_agent, {}, dependencies=["step1"])
        workflow.add_step("step3", mock_agent, {}, dependencies=["step1"])
        workflow.add_step("step4", mock_agent, {}, dependencies=["step2", "step3"])
        
        execution_order = workflow._resolve_dependencies()
        
        assert execution_order[0] == ["step1"]
        assert set(execution_order[1]) == {"step2", "step3"}
        assert execution_order[2] == ["step4"]
