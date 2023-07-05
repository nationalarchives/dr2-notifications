import unittest
from unittest.mock import MagicMock, Mock

from botocore.exceptions import ClientError

from lambda_function import get_entity_info_and_return_slack_message, get_slack_webhook_url, send_slack_message, \
    BaseHTTPResponse, verify_response


class TestNotificationsLambda(unittest.TestCase):

    def test_get_entity_info_and_return_slack_message(self):
        mock_record = {
                'messageId': '19dd0b57-b21e-4ac1-bd88-01bbb068cb78',
                'receiptHandle': 'MessageReceiptHandle',
                'body': '{"AlarmName": "test-alarm-name", "NewStateValue":"ALARM"}',
                'attributes': {
                   'ApproximateReceiveCount': '1',
                   'SentTimestamp': '1523232000000',
                   'SenderId': '123456789012',
                   'ApproximateFirstReceiveTimestamp': '1523232000001'
                },
                'messageAttributes': {},
                'md5OfBody': '{{{md5_of_body}}}',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-east-1:123456789012:MyQueue',
                'awsRegion': 'us-east-1'
             }
        slack_message = get_entity_info_and_return_slack_message(mock_record)
        self.assertEqual(f"Cloudwatch alarm test-alarm-name has entered state ALARM", slack_message)

    def test_get_slack_webhook_url_should_return_url_if_all_good(self):
        client = Mock()
        client.get_parameter = MagicMock(
            return_value={"Parameter": {"Value": "https://mockWebhookUrl.com"}}
        )
        slack_webhook_url = get_slack_webhook_url(client, "/secret/slack/mockSecretName")
        client.get_parameter.assert_called_with(Name="/secret/slack/mockSecretName", WithDecryption=True)

        self.assertEqual(slack_webhook_url, "https://mockWebhookUrl.com")

    def test_get_slack_webhook_url_should_throw_error_if_client_error(self):
        client = Mock()
        client.get_parameter = Mock(
            side_effect = ClientError({"Error": {"Code": "ErrorCode"}}, "")
        )

        with self.assertRaises(ClientError) as context:
            get_slack_webhook_url(client, "mockSecretName")

        self.assertTrue("An error occurred (ErrorCode) when calling the  operation: Unknown" in str(context.exception))

    def test_send_slack_message_pass_correct_args(self):
        http = Mock()
        response = BaseHTTPResponse()
        response.status = 200
        http.request = Mock(
            return_value = response
        )

        response = send_slack_message(http.request, "https://mockWebhookUrl.com", b"encodedbytes")

        http.request.assert_called_with("POST",
                                        "https://mockWebhookUrl.com",
                                        headers = {"Content-type": "application/json"},
                                        body = b"encodedbytes")

    def test_verify_response_should_return_string_if_under_400(self):
        http = Mock()
        response = BaseHTTPResponse()
        response.status = 300
        http.request = Mock(
            return_value = response
        )

        response = verify_response(response)

        self.assertEqual(response, "Response was 300")

    def test_verify_response_should_return_error_if_400_or_over(self):
        response = BaseHTTPResponse()
        response.status = 400
        response.data = "no_text"

        with self.assertRaises(Exception) as context:
            verify_response(response)

        self.assertTrue("Error: Request returned status code: 400 with a response of: no_text" in str(context.exception))


if __name__ == '__main__':
    unittest.main()
