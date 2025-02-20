import os
from dotenv import load_dotenv

load_dotenv()

class BaseConfig:
    """Base configuration with shared settings."""
    AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    PRIORITY_QUEUE = os.getenv("P2_QUEUE_URL", "https://prod-queue-url")
    TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "https://prod-teams-url")

    JIRA_SERVER = os.getenv("JIRA_SERVER", "https://server.com")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL","default@mail.com")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN","api_token")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY","project_key")


class TestConfig(BaseConfig):
    """Test configuration with mock settings"""
    def __init__(self,queue_url):
        self.PRIORITY_QUEUE = queue_url
