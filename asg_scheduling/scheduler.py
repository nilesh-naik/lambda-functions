import boto3
import requests
import iso8601
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from ast import literal_eval

now = datetime.now(timezone.utc)
secret_name = 'application_api_key'
region_name = 'us-west-2'
autoscaling_groups = {
    'backend-api-lc-20190610-v1': {
        'reserved': 2, 'ondemand': 6
    },
    'backend-dj-lc-20190610-V1': {
        'reserved': 1, 'ondemand': 2
    }
}

session = boto3.session.Session()

# Create a Secrets Manager client
sm_client = session.client(
    service_name='secretsmanager',
    region_name=region_name
)

# Create a Autoscaling Group client
asg_client = session.client(
    service_name='autoscaling',
    region_name=region_name
)


def schedule_asg_activity(name, client, group, start_time, capacity):
    """Schedule ASG group activity."""
    try:
        client.put_scheduled_update_group_action(
            AutoScalingGroupName=group,
            ScheduledActionName=(name),
            StartTime=start_time,
            MinSize=capacity,
            MaxSize=capacity*2,
            DesiredCapacity=capacity
        )
    except ClientError as e:
        raise e
    return


def schedule_scaling(event, context):
    """ Set schedule for auto scaling."""

    # Get currently scheduled scaledown time if any.
    scaledown_time = None
    scaledown_times = []
    sceduled_actions = asg_client.describe_scheduled_actions(
        # Set name of first asg from autoscaling_groups dict.
        AutoScalingGroupName=next(iter(autoscaling_groups)),
    )['ScheduledUpdateGroupActions']

    if sceduled_actions:
        for action in sceduled_actions:
            if action['ScheduledActionName'] == 'ScaleDown':
                scaledown_times.append(action['StartTime'])
        if scaledown_times:
            scaledown_time = max(scaledown_times)

    # Fetch API key from Secrets Manager.
    try:
        get_secret_value_response = sm_client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using
            # the provided KMS key.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for
            # the current state of the resource.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        secret = get_secret_value_response['SecretString']

    # Convert API key from str to dict.
    payload = literal_eval(secret)

    # Send an API call to fetch event schedule.
    event_response = requests.get(
        'https://example.com/v1/classes/event/objects',
        params=payload
    )

    # Go through events and check all the show dates.
    show_timings = []
    for event in event_response.json()['objects']:
        for show in event['showings']:
            dt = iso8601.parse_date(show['start_date_time'])
            show_timings.append(dt)

    # Add show time to list if show time is in next 25 hours.
    show_time = [t for t in show_timings
                 if now <= t <= now+timedelta(hours=25)]

    if show_time:
        new_scaleup_time = now + timedelta(hours=1)
        new_scaledown_time = now + timedelta(hours=25)

        if scaledown_time and new_scaleup_time <= scaledown_time:
            # Delete currenlty scheduled scale down actions.
            for asg in autoscaling_groups:
                asg_client.delete_scheduled_action(
                    AutoScalingGroupName=asg,
                    ScheduledActionName='ScaleDown'
                )
            # Schedule new scaledown action.
            for asg in autoscaling_groups:
                schedule_asg_activity('ScaleDown', asg_client, asg,
                                      new_scaledown_time,
                                      autoscaling_groups[asg]['reserved'])
            # End the function.
            return

        # Schedule new scaleup action.
        for asg in autoscaling_groups:
            schedule_asg_activity('ScaleUp', asg_client, asg, new_scaleup_time,
                                  (autoscaling_groups[asg]['reserved']
                                   + autoscaling_groups[asg]['ondemand']))

        # Schedule new scaledown action.
        for asg in autoscaling_groups:
            schedule_asg_activity('ScaleDown', asg_client, asg,
                                  new_scaledown_time,
                                  autoscaling_groups[asg]['reserved'])
        # End the function.
        return

    else:
        # Send an API call to fetch games schedule.
        game_response = requests.get(
            'https://example.com/v1/classes/game_schedule/objects',
            params=payload
        )

        # Go through games schedule and check all game date and timings.
        game_timings = []
        for game in game_response.json()['objects']:
            tm = iso8601.parse_date(game['date_iso'])
            game_timings.append(tm)

        # Add game time to list if game time is in next 25 hours.
        game_time = [t for t in game_timings
                     if now <= t <= now+timedelta(hours=25)]

        if game_time:
            new_scaleup_time = game_time[0] - timedelta(hours=2)
            new_scaledown_time = game_time[0] + timedelta(hours=6)

            if scaledown_time and new_scaleup_time <= scaledown_time:
                # Delete currenlty scheduled scale down actions.
                for asg in autoscaling_groups:
                    asg_client.delete_scheduled_action(
                        AutoScalingGroupName=asg,
                        ScheduledActionName='ScaleDown'
                    )
                # Schedule new scaledown action.
                for asg in autoscaling_groups:
                    schedule_asg_activity('ScaleDown', asg_client, asg,
                                          new_scaledown_time,
                                          autoscaling_groups[asg]['reserved'])
                # End the function.
                return

            # Schedule new scaleup action.
            for asg in autoscaling_groups:
                schedule_asg_activity('ScaleUp', asg_client, asg,
                                      new_scaleup_time,
                                      (autoscaling_groups[asg]['reserved']
                                       + autoscaling_groups[asg]['ondemand']))

            # Schedule new scaledown action.
            for asg in autoscaling_groups:
                schedule_asg_activity('ScaleDown', asg_client, asg,
                                      new_scaledown_time,
                                      autoscaling_groups[asg]['reserved'])
            # End the function.
            return
