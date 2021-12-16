#!/usr/bin/env python3
""" Publish link to download CodeBuild artifacts to Slack and Email. """

import boto3
import re
import os
import json
from datetime import datetime, timedelta, timezone
from botocore.client import Config
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from base64 import b64decode


# The base-64 encoded, encrypted access & secret keys (CiphertextBlob)
# stored in the environment variables
ENCRYPTED_ACCESS_KEY = os.environ['lambda_user_access_key']
ENCRYPTED_SECRET_KEY = os.environ['lambda_user_secret_key']
# Decrypt the access & secret key.
DECRYPTED_ACCESS_KEY = boto3.client('kms').decrypt(
                       CiphertextBlob=b64decode(ENCRYPTED_ACCESS_KEY)
                       )['Plaintext'].decode('utf-8')
DECRYPTED_SECRET_KEY = boto3.client('kms').decrypt(
                       CiphertextBlob=b64decode(ENCRYPTED_SECRET_KEY)
                       )['Plaintext'].decode('utf-8')
TZ = timezone(timedelta(hours=5.5))
NOW = datetime.now(TZ)
TIMESTR = NOW.strftime("%Y-%m-%dT%H:%M:%S")
SENDER = "noreply@example.com"
RECIPIENT = os.environ['Recipient']
CONFIGURATION_SET = "notifications"
AWS_REGION = "us-west-2"
SUBJECT = "Artifacts from build executed at " + TIMESTR
BODY_TEXT = "Hello,\r\nPlease use below link to access artifacts archive.\r\n"
BODY_HTML = """\
<html>
<head></head>
<body>
Hello,
<p>Please use below link to access artifacts archive.</p>
</body>
</html>
"""
CHARSET = "utf-8"
TARGET_LAMBDA = "xxxxxxxxx:function:pipeline-to-slack-notifications"
# s3_client is used to generate pre-signed URL. s3_client uses IAM user
# credentials instead of IAM role for Lambda as the URL generated remains valid
# for 7 days as oppossed to 6 hours when generated using role.
s3_client = boto3.client(
            's3',
            aws_access_key_id=DECRYPTED_ACCESS_KEY,
            aws_secret_access_key=DECRYPTED_SECRET_KEY,
            config=Config(signature_version='s3v4'))
ses_client = boto3.client('ses', region_name=AWS_REGION)
lambda_client = boto3.client('lambda')


def lambda_handler(event, context):
    # Get the object from the event and show its content type
    location = (event['detail']['additional-information']
                ['artifact']['location'])

    # Create a pattern to extract bucket name and key name from location.
    pattern = re.compile(r'.*:([\w-]+)/(.*)')

    # Match the pattern against the location.
    match_obj = pattern.search(location)

    # Extract bucket name and key name.
    bucket = match_obj.group(1)
    key = match_obj.group(2)

    # Get CodeBuild project name from event.
    project_name = (event['detail']['project-name'])

    try:
        # Generate presigned URL that can be accessed without authentication
        # and will expire in 7 days.
        object_url = s3_client.generate_presigned_url('get_object',
                                                      Params={'Bucket': bucket,
                                                              'Key': key},
                                                      ExpiresIn=604800)
        print(object_url)
    except Exception as e:
        print(e)
        print('Error generating URL for object {} from bucket {}.'.
              format(key, bucket))
        raise e

    # Construct and send email.
    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = project_name + ': ' + SUBJECT
    msg['From'] = SENDER
    msg['To'] = RECIPIENT

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # Encode the text and HTML content and set the character encoding.
    # This step is necessary if you're sending a message with characters
    # outside the ASCII range.
    textpart = MIMEText(BODY_TEXT + object_url, 'plain')
    htmlpart = MIMEText(BODY_HTML + u'<a href=' + object_url +
                        '>Download Artifacts.</a></body></html>', 'html')

    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    # Attach the multipart/alternative child container to
    # the multipart/mixed parent container.
    msg.attach(msg_body)

    try:
        # Provide the contents of the email.
        ses_client.send_raw_email(
            Source=SENDER,
            Destinations=[
                RECIPIENT
            ],
            RawMessage={
                'Data': msg.as_string(),
            },
            ConfigurationSetName=CONFIGURATION_SET
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent!")
    # Finished sending email.

    # Construct Slack message.
    message = {
        "text": "Artifacts generated for project {}.".format(project_name),
        "attachments": [
            {
                "fallback": "Download link: {}".format(object_url),
                "actions": [
                    {
                        "type": "button",
                        "text": "Download artifacts!",
                        "url": object_url,
                        "style": "primary"
                    }
                ]
            }
        ]
    }

    # Invoke lambda function to send message to Slack.
    lambda_client.invoke(
        FunctionName=TARGET_LAMBDA,
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(message)
    )
    # Finished sending Slack message.

    return
