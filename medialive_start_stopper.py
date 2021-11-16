'''
Copyright (c) 2021 Scott Cunningham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Summary: This script is a custom resource to place the HTML pages and Lambda code into the destination bucket.

Original Author: Scott Cunningham
'''

import boto3
import logging
import os
import datetime

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TAGNAME = os.environ['TAGKEY']
REGIONS = os.environ['REGIONS']

def lambda_handler(event, context):

    channel_action = event['Action'].lower()

    LOGGER.info("Checking day of the week...")
    days_of_week = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]

    int_day_of_week = datetime.datetime.today().weekday()

    if int_day_of_week < 5:
        LOGGER.info("Today is %s, continuing with script" % (days_of_week[int_day_of_week]))
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

    else:
        LOGGER.warning("Today is %s, no need to run automation.." % (days_of_week[int_day_of_week]))
        return "Today is %s, no need to run automation.." % (days_of_week[int_day_of_week])
