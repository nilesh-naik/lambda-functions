import logging
import boto3
import local_config
from chef import Node, Search, Client, ChefAPI
from base64 import b64decode
from botocore.exceptions import ClientError
from chef.exceptions import ChefServerNotFoundError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
REGION = local_config.REGION
USERNAME = local_config.USERNAME
VERIFY_SSL = local_config.VERIFY_SSL
DEBUG = local_config.DEBUG


def get_asg_name(event):
    """Gets ASG name from CloudWatch event"""
    return event['detail']['AutoScalingGroupName']


def set_chef_url(asg_name):
    """Sets Chef server url based on autoscaling group name"""
    return {
        'autoscaling-group':
        'https://ip-xxx-xxx-xx-x.ec2.internal/organizations/acme'
    }[asg_name]


def log_event(event):
    """Logs event information for debugging"""
    LOGGER.info("----------------------------------------------------")
    LOGGER.info(event)
    LOGGER.info("----------------------------------------------------")


def get_instance_id(event):
    """Parses EC2InstanceId from the event dict"""
    try:
        return event['detail']['EC2InstanceId']
    except KeyError as err:
        LOGGER.error(err)
        return False


def get_pem():
    """Decrypt the CiphertextBlob to get janitors's pem file"""
    try:
        with open('encrypted_pem.txt', 'r') as encrypted_pem:
            pem_file = encrypted_pem.read()

        kms = boto3.client('kms', region_name=REGION)
        return kms.decrypt(CiphertextBlob=b64decode(pem_file))['Plaintext']

    except (IOError, ClientError, KeyError) as err:
        LOGGER.error(err)
        return False


def lambda_handler(event, context):
    log_event(event)
    ASG_NAME = get_asg_name(event)
    CHEF_SERVER_URL = set_chef_url(ASG_NAME)

    with ChefAPI(CHEF_SERVER_URL, get_pem(), USERNAME, ssl_verify=VERIFY_SSL):
        instance_id = get_instance_id(event)
        try:
            search = Search('node', 'instance_id:' + instance_id)
        except ChefServerNotFoundError as err:
            LOGGER.error(err)
            return False

        if len(search) != 0:
            for instance in search:
                node = Node(instance.object.name)
                client = Client(instance.object.name)
                try:
                    LOGGER.info('Deleting node ' + node.name)
                    LOGGER.info('Deleting client ' + client.name)
                    if not DEBUG:
                        node.delete()
                        LOGGER.info('Node deleted successfully.')
                        client.delete()
                        LOGGER.info('Client deleted successfully.')
                    else:
                        LOGGER.info(
                            'Would have deleted the node named {}, '
                            'but we are in DEBUG mode.'
                        ).format(node)
                        LOGGER.info(
                            'Would have deleted the client named {}, '
                            'but we are in DEBUG mode.'
                        ).format(client)
                    return True
                except ChefServerNotFoundError as err:
                    LOGGER.error(err)
                    return False
        else:
            LOGGER.info(
                'Instance {} does not appear to be managed by Chef.'
            ).format(instance_id)
            return True
