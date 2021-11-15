import json
import boto3
import logging
import os

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TAGNAME = os.environ['TAGKEY']
REGIONS = os.environ['REGIONS']

def lambda_handler(event, context):

    channel_action = event['Action'].lower()

    LOGGER.info("Starting MediaLive Run Scheduler. Action to perform %s : " % (channel_action) )

    # Convert regions argument to a list to iterable list
    if "," in REGIONS:
        regions = REGIONS.split(",")
    else:
        regions = [REGIONS]

    LOGGER.info("Initializing MediaLive Schedule Cleanup Script...")
    LOGGER.info("Regions to iterate through : %s " % (regions))

    # Create a dict to contain all response data when the actions have been performed in each region
    execution_response = dict()

    for region in regions:

        LOGGER.info("Iterating through region: %s" % (region))

        # initialize boto3 client for region
        medialive_client = boto3.client('medialive', region_name=region)

        # capture channel response to variable
        medialive_channels = medialive_client.list_channels(MaxResults=100)

        if len(medialive_channels['Channels']) < 1:
            LOGGER.info("No medialive channels present in region : %s " % (region) )

        else:

            LOGGER.info("Found %s MediaLive channels in %s" % (len(medialive_channels['Channels']),region))

            # Iterate through returned channels
            channel_list = []
            for channel in medialive_channels['Channels']:

                # Do check for Tags attached to channel. Only delete schedule actions for channels part of the correct project
                if len(channel['Tags']) == 0 or TAGNAME not in channel['Tags']:
                    LOGGER.info("Channel %s not a part of the run schedule workflow and so taking no action..." % (channel['Id']))

                else:

                    # Grab the channel Id and append it to the list to execute on
                    channel_id = channel['Id']
                    channel_list.append(channel_id)

            # Stop channels that are in the list
            if len(channel_list) > 0:
                # there are channels to start/stop

                LOGGER.info("Channels to perform action on in %s : %s" % (region,channel_list))

                if channel_action == "start":
                    # batch start
                    try:
                        response = medialive_client.batch_start(ChannelIds=channel_list)
                        execution_response[region] = response
                        LOGGER.info("Task complete in region %s" % (region))
                    except Exception as e:
                        LOGGER.warning("Got exception when trying to start channels: %s " % (e))
                        execution_response[region] = {"Action Failed":e}

                elif channel_action == "stop":
                    # batch stop
                    try:
                        response = medialive_client.batch_stop(ChannelIds=channel_list)
                        execution_response[region] = response
                    except Exception as e:
                        LOGGER.warning("Got exception when trying to stop channels: %s " % (e))
                        execution_response[region] = {"Action Failed":e}

                else:
                    # Should not get here. there is a mistake in the CloudWatch event rule
                    LOGGER.error("Cant do anything... expecting channel action to be start or stop, got %s instead. Fix in CloudWatch Event rule" % (channel_action))
                    execution_response[region] = {"Action Failed": "Cant do anything... expecting channel action to be start or stop, got %s instead. Fix in CloudWatch Event rule" % (channel_action)}

    return execution_response