#!/usr/bin/env python3
""" Send notifications from pipelines to Slack. """

import boto3
import json
import logging
import os
import requests

from base64 import b64decode

# The base-64 encoded, encrypted key (CiphertextBlob)
# stored in the kmsEncryptedHookUrl environment variable
ENCRYPTED_HOOK_URL = os.environ['kmsEncryptedHookUrl']

HOOK_URL = 'https://' + boto3.client('kms').decrypt(
        CiphertextBlob=b64decode(ENCRYPTED_HOOK_URL)
    )['Plaintext'].decode('utf-8')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info('Event: ' + str(event))

    # Construct message.
    if 'attachments' in event:
        # message is about artifact
        message = json.dumps(event)
    elif 'stage' in event['detail']:
        # message is about pipeline stage
        pipeline = event['detail']['pipeline']
        stage = event['detail']['stage']
        state = event['detail']['state']
        message = json.dumps({
            'text': 'Pipeline {}\'s *{}* stage {}.'.format(
                pipeline, stage, state.lower()
            )
        })
    else:
        # message is about pipeline state
        pipeline = event['detail']['pipeline']
        state = event['detail']['state']
        message = json.dumps({
            'text': 'Pipeline {} {}.'.format(pipeline, state.lower())
        })

    logger.info('Message: ' + message)

    headers = {'Content-Type': 'application/json'}

    try:
        requests.post(HOOK_URL, data=message, headers=headers)
    except Exception as e:
        logger.error("Request failed: %s", e)
