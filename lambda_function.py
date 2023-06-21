import urllib3
from botocore.client import BaseClient
import json
import os
import boto3
from botocore.exceptions import ClientError

http = urllib3.PoolManager()


class BaseHTTPResponse:
    status: int
    data: bytes


def get_entity_info_and_return_slack_message(record: dict) -> str:
    body = json.loads(record["body"])
    entity_ref: str = body["ref"]

    slack_message = f"A SQS message containing the entity ref: _*{entity_ref}*_ was sent to the _*DLQ*_"
    return slack_message


def get_slack_webhook_url(session_client: BaseClient, secret_name: str) -> str:
    try:
        get_secret_value_response = session_client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e

    secret_json_string: str = get_secret_value_response["SecretString"]
    secret_json = json.loads(secret_json_string)
    url: str = secret_json["slack_webhook_url"]
    return url


def send_slack_message(request, slack_webhook_url: str, encoded_json_string: bytes) -> BaseHTTPResponse:
    return request(
        "POST",
        slack_webhook_url,
        headers = {"Content-type": "application/json"},
        body = encoded_json_string
    )


def verify_response(response: BaseHTTPResponse) -> str:
    if response.status >= 400:
        raise Exception(f"Error: Request returned status code: {response.status} with a response of: {response.data}")
    else:
        return f"Response was {response.status}"


def lambda_handler(event, context):
    webhook_secret_name = os.environ["WEBHOOK_SECRET_NAME"]
    records: list[dict] = event["Records"]

    session = boto3.session.Session()
    session_client: BaseClient = session.client(service_name="secretsmanager", region_name="eu-west-2")

    for record in records:
        slack_message = get_entity_info_and_return_slack_message(record)
        slack_message_in_json = {"text": slack_message}

        encoded_json_string: bytes = json.dumps(slack_message_in_json, indent=2).encode("utf-8")
        slack_webhook_url = get_slack_webhook_url(session_client, webhook_secret_name)

        resp: BaseHTTPResponse = send_slack_message(http.request, slack_webhook_url, encoded_json_string)
        verify_response(resp)
