import boto3
import re
from datetime import datetime, timedelta, timezone
from botocore.client import Config
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


TZ = timezone(timedelta(hours=5.5))
NOW = datetime.now(TZ)
TIMESTR = NOW.strftime("%Y-%m-%dT%H:%M:%S")
SENDER = "sender@example.com"
RECIPIENT = "recipient@example.com"
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
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
ses_client = boto3.client('ses', region_name=AWS_REGION)


def artifact_handler(event, context):
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

    return
