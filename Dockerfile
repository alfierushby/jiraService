From python:3.9.21-alpine3.21
WORKDIR /app
COPY  requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
EXPOSE 8000
ENV P2_QUEUE_URL=""
ENV AWS_REGION=""
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""
ENV JIRA_SERVER=""
ENV JIRA_PROJECT_KEY=""
ENV JIRA_EMAIL=""
ENV JIRA_API_TOKEN=""
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-c","gunicorn_config.py","app:create_app()"]
