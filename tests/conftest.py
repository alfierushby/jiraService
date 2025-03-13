import json
import os

import boto3
import pytest
from unittest.mock import patch, MagicMock, Mock
from config import TestConfig
from app import create_app
from moto import mock_aws

mock_body = Mock()
mock_body.read.return_value = json.dumps({"results": [{"outputText": "Testing"}]})
mock_response = {"body": mock_body}

@pytest.fixture
def app():
    """Create and configure a new Flask app instance for testing
    :return: app created
    """
    with patch("jira.JIRA") as MockJIRA:
        with mock_aws():
            sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION"))

            #  Create mock queue
            queue = sqs.create_queue(QueueName="test")["QueueUrl"]

            # Mock bedrock
            bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
            bedrock.invoke_model = MagicMock(return_value=mock_response)

            # Override the send message to be true
            mock_jira_instance = MagicMock()
            mock_jira_instance.create_issue.return_value = True # True for sent issue
            MockJIRA.return_value = mock_jira_instance  # Return mock instance

            # Override priority queues with test values
            config = TestConfig(queue_url=queue)

            app = create_app(config=config,jira_client=mock_jira_instance,bedrock_client=bedrock)

            yield app

@pytest.fixture
def client(app):
    """Create a test client for the Flask app
    :param app: The flask app
    :return: The app with a test client created
    """
    return app.test_client()
