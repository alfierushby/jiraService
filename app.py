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

from config import BaseConfig

stop_event = threading.Event()

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


def poll_sqs_jira_loop(sqs_client, jira_client, config):
    """
    Constantly checks SQS queue for messages and processes them to send to jira if possible
    """
    while not stop_event.is_set():
        try:
            response = sqs_client.receive_message(
                QueueUrl=config.PRIORITY_QUEUE, WaitTimeSeconds=20)

            messages = response.get("Messages", [])

            if not messages:
                print("No messages available")
                continue

            for message in messages:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])

                handled_body = Request(**body).model_dump()

                gunicorn_logger.info(f"Message Body: {handled_body}")

                issue_data = {
                    "project": {"key": config.JIRA_PROJECT_KEY},
                    "summary": handled_body["title"],
                    "description": handled_body["description"],
                    "issuetype": {"name": "Task"}
                }

                jira_client.create_issue(fields=issue_data)

                request_counter.labels(priority="High").inc()

                sqs_client.delete_message(QueueUrl=config.PRIORITY_QUEUE, ReceiptHandle=receipt_handle)

        except Exception as e:
            # Use logging instead!!
            gunicorn_logger.info(f"Error, cannot poll: {e}.")


def create_app(sqs_client=None, jira_client=None, config=None):
    app = Flask(__name__)

    # Initialize Prometheus Metrics once
    metrics = PrometheusMetrics(app)

    if config is None:
        config = BaseConfig()
    if sqs_client is None:
        sqs_client = boto3.client('sqs', region_name=config.AWS_REGION)
    if jira_client is None:
        jira_client = JIRA(server=config.JIRA_SERVER, basic_auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN))

    sqs_thread = threading.Thread(target=poll_sqs_jira_loop, args=(sqs_client, jira_client,config), daemon=True)
    sqs_thread.start()

    # Store configuration in app config for other entities
    app.config.from_object(config)

    @app.route('/health', methods=["GET"])
    def health_check():
        """ Checks health, endpoint """
        return jsonify({"status": "healthy"}), 200

    return app


if __name__ == '__main__':
    create_app().run()
