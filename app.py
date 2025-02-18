import json
import os
import threading
import logging

from flask import Flask, jsonify
import boto3
from jira import JIRA
from dotenv import load_dotenv
from prometheus_flask_exporter import PrometheusMetrics, Counter
from pydantic import Field, BaseModel


stop_event = threading.Event()
load_dotenv()

AWS_REGION = os.getenv('AWS_REGION')
P2_QUEUE_URL = os.getenv('P2_QUEUE_URL')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL')
ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
ACCESS_SECRET = os.getenv('AWS_SECRET_ACCESS_KEY')

JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

request_counter = Counter(
    "priority_requests_total",
    "Total priority requests processed",
    labelnames=["priority"]
)

gunicorn_logger = logging.getLogger("gunicorn.error")

# Want the minimum length to be at least 1, otherwise "" can be sent which breaks certain APIs.
class Request(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: str = Field(..., min_length=1)

def poll_sqs_jira_loop(sqs_client, jira_client):
    """
    Constantly checks SQS queue for messages and processes them to send to jira if possible
    """
    while not stop_event.is_set():
        try:
            response = sqs_client.receive_message(
                QueueUrl=P2_QUEUE_URL, WaitTimeSeconds=2)

            messages = response.get("Messages", [])

            if not messages:
                # Use logging instead!!
                gunicorn_logger.info("No messages available")
                continue

            for message in messages:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])

                handled_body = Request(**body).model_dump()

                gunicorn_logger.info(f"Message Body: {handled_body}")

                issue_data = {
                    "project": {"key": JIRA_PROJECT_KEY},
                    "summary": handled_body["title"],
                    "description": handled_body["description"],
                    "issuetype": {"name": "Task"}
                }

                jira_client.create_issue(fields=issue_data)

                request_counter.labels(priority="High").inc()

                sqs_client.delete_message(QueueUrl=P2_QUEUE_URL, ReceiptHandle=receipt_handle)

        except Exception as e:
            # Use logging instead!!
            gunicorn_logger.info(f"Error, cannot poll: {e}")

def create_app():
    app = Flask(__name__)

    # Initialize Prometheus Metrics once
    metrics = PrometheusMetrics(app)

    sqs_client = boto3.client('sqs', region_name=AWS_REGION, aws_access_key_id=ACCESS_KEY,
                              aws_secret_access_key=ACCESS_SECRET)
    jira_client = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

    sqs_thread = threading.Thread(target=poll_sqs_jira_loop,args=(sqs_client,jira_client), daemon=True)
    sqs_thread.start()


    @app.route('/health',methods=["GET"])
    def health_check():
        """ Checks health, endpoint """
        return jsonify({"status":"healthy"}),200

    return app

if __name__ == '__main__':
    create_app().run()