import os
import threading

from flask import Flask, jsonify
import boto3
from jira import JIRA
from dotenv import load_dotenv

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

app = Flask(__name__)


def poll_sqs_teams_loop():
    """
    Constantly checks SQS queue for messages and processes them to send to teams if possible
    """
    while True:
        try:
            response = sqs_client.receive_message(
                QueueUrl=P2_QUEUE_URL,WaitTimeSeconds=20)

            messages = response.get("Messages",[])

            if not messages:
                print("No messages available")
                continue

            for message in messages:
                receipt_handle = message['ReceiptHandle']
                message = eval(message['Body'])

                print(f"Message Body: {message}")

                issue_data = {
                    "project":{"key":JIRA_PROJECT_KEY},
                    "summary": message["title"],
                    "description": message["description"],
                    "issuetype": {"name": "Task"}
                }

                jira_client.create_issue(fields=issue_data)

                sqs_client.delete_message(QueueUrl=P2_QUEUE_URL,ReceiptHandle=receipt_handle)

        except Exception as e:
            print(f"Error, cannot poll: {e}")



@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


if __name__ == '__main__':
    sqs_client = boto3.client('sqs', region_name=AWS_REGION, aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=ACCESS_SECRET)
    jira_client = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    print("test")
    sqs_thread = threading.Thread(target=poll_sqs_teams_loop,daemon=True)
    sqs_thread.start()
    app.run()
