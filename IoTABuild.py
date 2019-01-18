import json
import boto3
import os
import traceback
import sys


def createIoTA():
    # The following code will get the necessary configuration JSON from the local directory on the EC2 instance
    tmpdir = os.getenv("TMP_DIR", "/home/ec2-user")
    filename = "IoTAconfig.json"
    tmpfile = os.path.join(tmpdir, os.path.basename(filename))
    exists = os.path.isfile(tmpfile) 
    # As long as the configuration file is there we will continue with the process
    if exists:
        # opens the configuration file and sets the necessary paramaters for the approppriate clients
        with open('IoTAconfig.json') as f:
            IoTAConfig = json.load(f)  
        region_name = IoTAConfig['region']
        iota = boto3.client('iotanalytics', region_name=region_name)
        iot = boto3.client('iot', region_name=region_name)
        iam = boto3.client('iam', region_name=region_name)
        # First creates the datastore as that needs to be created first before it can be attached to the pipeline
        ds = iota.create_datastore(
            datastoreName=IoTAConfig["datastoreName"],
            retentionPeriod = {
                "unlimited" : True
            },
            tags = [
                {
                    "key" : IoTAConfig['tagkey'],
                    "value" : IoTAConfig['tagvalue']
                }
            ]
        )
        print("ds:{}".format(ds))
        # Then we create the channel as this also needs to be created before the pipeline
        channel = iota.create_channel(
            channelName = IoTAConfig["channelName"],
            retentionPeriod={
                "unlimited" : True
            },
            tags=[
                {
                    "key" : IoTAConfig['tagkey'],
                    "value" : IoTAConfig['tagvalue']   
                }
            ]
        )
        print("channel: {}".format(channel))
        # The followig information has been placed here as a comment about the other "categfories" that can be added 
        # to the pipeline activities
        # {
        #     'channel': {
        #         'name': 'string',
        #         'channelName': 'string',
        #         'next': 'string'
        #     },
        #     'lambda': {
        #         'name': 'string',
        #         'lambdaName': 'string',
        #         'batchSize': 123,
        #         'next': 'string'
        #     },
        #     'datastore': {
        #         'name': 'string',
        #         'datastoreName': 'string'
        #     },
        #     'addAttributes': {
        #         'name': 'string',
        #         'attributes': {
        #             'string': 'string'
        #         },
        #         'next': 'string'
        #     },
        #     'removeAttributes': {
        #         'name': 'string',
        #         'attributes': [
        #             'string',
        #         ],
        #         'next': 'string'
        #     },
        #     'selectAttributes': {
        #         'name': 'string',
        #         'attributes': [
        #             'string',
        #         ],
        #         'next': 'string'
        #     },
        #     'filter': {
        #         'name': 'string',
        #         'filter': 'string',
        #         'next': 'string'
        #     },
        #     'math': {
        #         'name': 'string',
        #         'attribute': 'string',
        #         'math': 'string',
        #         'next': 'string'
        #     },
        #     'deviceRegistryEnrich': {
        #         'name': 'string',
        #         'attribute': 'string',
        #         'thingName': 'string',
        #         'roleArn': 'string',
        #         'next': 'string'
        #     },
        #     'deviceShadowEnrich': {
        #         'name': 'string',
        #         'attribute': 'string',
        #         'thingName': 'string',
        #         'roleArn': 'string',
        #         'next': 'string'
        #     }
        # },
        # Here we are setting what we want as the pipeline activities. This is a very vanilla pipeline build.
        # The activities listed here connect the pieces of the pipeline together.
        dactivity=[
            {
                "channel": {
                        "channelName": channel["channelName"],
                        "name": IoTAConfig["channelName"],
                        "next" : IoTAConfig["datastoreName"]
                }
            },
            {
                "datastore": {
                        "datastoreName": ds["datastoreName"],
                        "name": IoTAConfig["datastoreName"]
                }
            }
        ]

        print("dactivity: {}".format(dactivity))
        print("length", len(dactivity))
        # This creates the pipeline
        pipeline = iota.create_pipeline(
            pipelineActivities = dactivity,           
            pipelineName = IoTAConfig["pipelineName"]
        )
        print("pipeline: {}".format(pipeline))
        # This is the SQL that will run that will be used to populate the dataset
        sql = "SELECT * FROM " + ds["datastoreName"]
        print("Sql", sql)
        # This will create the dataset that will provide the data for the Ml Notebooks
        dataset = iota.create_dataset(
            datasetName=IoTAConfig['datasetName'],
            actions=[
                {
                    'actionName' : 'generalAction',
                    'queryAction': {
                        'sqlQuery': sql
                    },
                },
            ],
            triggers=[
                {
                    'schedule': {
                        'expression': "cron(0/15 * * * ? *)"
                    }
                },
            ],
            retentionPeriod={
                'unlimited': True
            },
            tags=[
                {
                    'key': IoTAConfig['tagkey'],
                    'value': IoTAConfig['tagvalue']
                },
            ]
        )
        print("dataset: {}".format(dataset))
        # This section will see if a role has already bee created for the creation of IoT Analytics. If not it will
        # create the role
        try:
            rolecheck2 = iam.get_role(
                RoleName = "XAutoGGIoTA"
            )
            print("Rolecheck: {}".format(rolecheck2))
            IoTARole = rolecheck2['Role']['Arn']
            role = "used existing role"
            assign = "used existing role"
        except:
            print("Error role is not found")
            rolePolicy = {
                "Version":"2012-10-17",
                "Statement":[
                    {"Effect":"Allow",
                    "Principal":{"Service":["iotanalytics.amazonaws.com"]},
                    "Action":["sts:AssumeRole"]}]    
            }
            print("rolepolicy", rolePolicy)
            role = iam.create_role(
                RoleName="XAutoGGIoTA",
                AssumeRolePolicyDocument = json.dumps(rolePolicy),
                Description = "Auto generated role"
            )
            print("role: {}".format(role))

            mypolicy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iotanalytics:BatchPutMessage",
                        "Resource": channel['channelArn']
                    }
                ]
            }
            assign = iam.put_role_policy(
                RoleName="XAutoGGIoTA",
                PolicyName="XAutoProvisionGGIoTA",
                PolicyDocument= json.dumps(mypolicy)
            )
            print("assign: {}".format(assign))
            IoTARole = role['Role']['Arn']

        # This sets up the sql for what information will be used in the topic capture
        sql2 = "SELECT * FROM '" + IoTAConfig['msgTopic'] + "'"
        print('sql', sql2)

        rulePayLoad = {
                'sql': sql2,
                'description': 'Autogenerated GG and IoTA Rule',
                'actions': [
                    {
                        'iotAnalytics': {
                            'channelArn': channel['channelArn'],
                            'channelName': channel['channelName'],
                            'roleArn': IoTARole
                            # 'roleArn': role['Role']['Arn']
                        },
                    },
                ],
                'ruleDisabled': False,
                'awsIotSqlVersion': '2016-03-23',
            } 
        print("rulePayload: {}". format(rulePayLoad))
        # This creates the Iot Rule
        IoTARule = iot.create_topic_rule(
            ruleName=IoTAConfig['ruleName'],
            topicRulePayload= rulePayLoad
        )
        print("IoTARule: {}". format(IoTARule))
        # This is just a nice little feature that creates an output file of what components were created and their information
        iotstate = {
                'datastore': ds,
                'channel': channel,
                'pipeline': pipeline,
                'dataset': dataset,
                'trustpolicy': role,
                'policy': assign,
                'IoT Rule': IoTARule
        }
        with open('./iotstate.json', 'w') as x:
            json.dump(iotstate, x, indent=4)


createIoTA()

print "IoT Analytics Build Complete"