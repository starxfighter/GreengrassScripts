import json
import yaml
import boto3
import os
import traceback
import sys

def checkGroup(groupin):
    notEndofList = True
    found = False
    groupCheck = gg.list_groups(
        MaxResults = '100'
    )
    print('groupcheck', groupCheck)
    if 'NextToken' in groupCheck:
        nextGroup = groupCheck['NextToken']
    while notEndofList:
        for x in range(len(groupCheck['Groups'])):
            if groupCheck['Groups'][x]['Name'] == groupin:
                result = groupCheck['Groups'][x]
                found = True    
        print('found', found)
        if found:
            notEndofList = False
        else:
            if 'NextToken' in groupCheck:
                groupCheck = gg.list_groups(
                    MaxResults = '100',
                    NextToken = groupCheck['NextToken']
                )   
            else:
                notEndofList = False 

    if not found:
        result = gg.create_group(
            Name=groupin
        )
    return result

def checkPolicy(policyNameIn, region):
    notEndofList = True
    found = False
    policyCheck = iot.list_policies(
        pageSize=100,
        ascendingOrder = True
    )
    # print("policyCheck", policyCheck)
    while notEndofList:
        for x in range(len(policyCheck['policies'])):
            if policyCheck['policies'][x]['policyName'] == policyNameIn:
                # print("foundpolicy match")
                result = policyCheck['policies'][x]
                found = True
            if found:
                notEndofList = False
            else:
                if 'nextMarker' in policyCheck:
                    policyCheck = iot.list_policies(
                        marker = policyCheck['nextMarker'],
                        pageSize = 100,
                        ascendingOrder = True    
                    )   
                else:
                    notEndofList = False
    # print("found", found)

    if not found:
        core_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["iot:Publish", "iot:Subscribe", "iot:Connect", "iot:Receive", "iot:GetThingShadow", "iot:DeleteThingShadow", "iot:UpdateThingShadow"],
                    "Resource": ["arn:aws:iot:" + region + ":*:*"]
                },
                {
                    "Effect": "Allow",
                    "Action": ["greengrass:AssumeRoleForGroup", "greengrass:CreateCertificate", "greengrass:GetConnectivityInfo", "greengrass:GetDeployment", "greengrass:GetDeploymentArtifacts", "greengrass:UpdateConnectivityInfo", "greengrass:UpdateCoreDeploymentStatus"],
                    "Resource": ["*"]
                }
            ]
        }
        result = iot.create_policy(
            policyName=policyNameIn,
            policyDocument=json.dumps(core_policy_doc))

    return result

def createLocalResource(groupname, name, source, destination):
    result =  gg.create_resource_definition(
        Name= groupname,
        InitialVersion={
            'Resources': [
                {
                    'Id': name,
                    'Name': 'TempDircetory',
                    'ResourceDataContainer': {
                        'LocalVolumeResourceData': {
                            'SourcePath': source,
                            'DestinationPath': destination,
                            'GroupOwnerSetting': {
                                'AutoAddGroupOwner': True,
                                'GroupOwner': ''
                            } 
                        }
                    }
                }
            ]
        }
    )

    return result

def checkLambda(config):
    try:
        check = clientLambda.get_function(
            FunctionName = config['lambdaARN'],
            Qualifier = config['lambdaAlias']
        )
        tempARN = config['lambdaARN'] + ':' + config['lambdaAlias']
        # tempLoRes = bool(config['createLocalRes'])
        if config['createLocalRes'] == "True":
            tempLoRes = True
        else:
            tempLoRes = False
        # print("local resource", tempLoRes, type(tempLoRes))
        # tempPinned = bool(config['lambdaLongLived'])
        if config['lambdaLongLived'] == "True":
            tempPinned = True
        else:
            tempPinned = False
        # print("long lived", tempPinned, type(tempPinned))
        if tempLoRes:
            result = gg.create_function_definition(
                Name=config['lambdaFunName'],
                InitialVersion={
                    'Functions': [
                        {
                            'Id': config['lambdaIdName'], 
                            'FunctionArn': tempARN,
                            'FunctionConfiguration': {
                                'Pinned': tempPinned,
                                'MemorySize': config['lambdaMemSize'],
                                'Timeout': config['lambdaTimeout'],
                                'Environment': {
                                    'AccessSysfs': False,
                                    'ResourceAccessPolicies': [
                                        {
                                            'ResourceId': config['LocResName'],
                                            'Permission': 'rw'
                                        }
                                    ]
                                } 
                            }
                        }
                    ]
                }
            )
        else:
            result = gg.create_function_definition(
                Name=config['lambdaFunName'],
                InitialVersion={
                    'Functions': [
                        {
                            'Id': config['lambdaIdName'], 
                            'FunctionArn': tempARN,
                            'FunctionConfiguration': {
                                'Pinned': tempPinned,
                                'MemorySize': config['lambdaMemSize'],
                                'Timeout': config['lambdaTimeout'],
                                'Environment': {
                                    'AccessSysfs': False,
                                } 
                            }
                        }
                    ]
                }
            )  
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print("Type error: " + str(e))
        print(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print "The lambda entered is not valid"
        result = "error"

    return result

def createSubscription(config):
    tempARN = config['lambdaARN'] + ':' + config['lambdaAlias']
    result = gg.create_subscription_definition(
        InitialVersion={
            'Subscriptions': [
                {
                    'Id': config['subscriptionIdName'],
                    'Source': tempARN,
                    'Subject': config['subscriptionSubject'],
                    'Target': 'cloud'
                }
            ]
        },
        Name=config['subscriptionName']
    )     

    return result

def createIoTA():
    tmpdir = os.getenv("TMP_DIR", "/home/ec2-user")
    filename = "IoTAconfig.json"
    tmpfile = os.path.join(tmpdir, os.path.basename(filename))
    exists = os.path.isfile(tmpfile) 
    if exists:
        with open('IoTAconfig.json') as f:
            IoTAConfig = json.load(f)  
        region_name = IoTAConfig['region']
        iota = boto3.client('iotanalytics', region_name=region_name)
        iot = boto3.client('iot', region_name=region_name)
        iam = boto3.client('iam', region_name=region_name)
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
        # cactivity =  [{ 
        #             "channel": { 
        #                 "channelName": channel["channelName"],
        #                 "name": IoTAConfig["channelName"]
        #             }
        #         }]
        # dactivity =  [{ 
        #             "channel": { 
        #                 "channelName": channel["channelName"],
        #                 "name": IoTAConfig["channelName"],
        #                 "next" : ds["datastoreName"]
        #             },
        #             "datastore": { 
        #                 "datastoreName": ds["datastoreName"],
        #                 "name": IoTAConfig["datastoreName"]
        #             }
        #         }]
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
        pipeline = iota.create_pipeline(
            pipelineActivities = dactivity,           
            pipelineName = IoTAConfig["pipelineName"]
        )
        print("pipeline: {}".format(pipeline))
        # pipeline = iota.update_pipeline(
        #     pipelineActivities = dactivity,           
        #     pipelineName = IoTAConfig["pipelineName"]   
        # )
        # print("pipeline: {}".format(pipeline))
        sql = "SELECT * FROM " + ds["datastoreName"]
        print("Sql", sql)
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
        # policy = {
        #         "Version": "2012-10-17",
        #         "Statement": [
        #         {
        #             "Effect": "Allow",
        #             "Action": "iotanalytics:BatchPutMessage",
        #             "Resource": channel['channelArn']
        #         }
        #     ]
        # }
        rolePolicy = {
            "Version":"2012-10-17",
            "Statement":[
                {"Effect":"Allow",
                "Principal":{"Service":["iotanalytics.amazonaws.com"]},
                "Action":["sts:AssumeRole"]}]    
        }
        print("rolepolicy", rolePolicy)
        role = iam.create_role(
            RoleName="AutoGGIoTA",
            AssumeRolePolicyDocument = json.dumps(rolePolicy),
            Description = "Auto generated role"
        )
        print("role: {}".format(role))
        # print("ruleArn", role['Role']['Arn'])
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
            RoleName="AutoGGIoTA",
            PolicyName="AutoProvisionGGIoTA",
            PolicyDocument= json.dumps(mypolicy)
        )
        print("assign: {}".format(assign))
        sql2 = "SELECT * FROM '" + IoTAConfig['msgTopic'] + "'"
        print('sql', sql2)
        # print("ruleArn", role['Arn'])
        rulePayLoad = {
                'sql': sql2,
                'description': 'Autogenerated GG and IoTA Rule',
                'actions': [
                    {
                        'iotAnalytics': {
                            'channelArn': channel['channelArn'],
                            'channelName': channel['channelName'],
                            'roleArn': role['Role']['Arn']
                        },
                    },
                ],
                'ruleDisabled': False,
                'awsIotSqlVersion': '2016-03-23',
            } 
        print("rulePayload: {}". format(rulePayLoad))
        IoTARule = iot.create_topic_rule(
            ruleName=IoTAConfig['ruleName'],
            topicRulePayload= rulePayLoad
        )
        print("IoTARule: {}". format(IoTARule))

# ************************************
# Beginning of the Main flow
# ************************************
tmpdir = os.getenv("TMP_DIR", "/home/ec2-user")
filename = "ggconfig.json"
tmpfile = os.path.join(tmpdir, os.path.basename(filename))
exists = os.path.isfile(tmpfile)

if exists:
    with open('ggconfig.json') as f:
        custConfig = json.load(f)
    region_name = custConfig['region']
    # Sets AWS Services that will be used
    gg = boto3.client('greengrass', region_name=region_name)
    iot = boto3.client('iot', region_name=region_name)
    clientLambda = boto3.client('lambda', region_name=region_name)
    gglambda = checkLambda(custConfig)
    # print("gglambda", gglambda)
    if gglambda != 'error':    
        group = checkGroup(custConfig['groupName'])
        keys_cert = iot.create_keys_and_certificate(setAsActive=True)
        core_thing = iot.create_thing(thingName="{0}_core".format(group['Name']))
        iot.attach_thing_principal(
            thingName=core_thing['thingName'],
            principal=keys_cert['certificateArn'])
        policy = checkPolicy(custConfig['policyName'], region_name)
        print("policy", policy)
        iot.attach_principal_policy(
            policyName=policy['policyName'],
            principal=keys_cert['certificateArn'])
        initial_version = {'Cores': [
            {
                'Id': core_thing['thingName'], # Quite intuitive, eh?
                'CertificateArn': keys_cert['certificateArn'],
                'SyncShadow': False, # Up to you, True|False
                'ThingArn': core_thing['thingArn']
            }
        ]}
        core_definition = gg.create_core_definition(
            Name="{0}_core_def".format(group['Name']),
            InitialVersion=initial_version)
        # tempLoRes = bool(custConfig['createLocalRes'])
        if custConfig['createLocalRes'] == "True":
            tempLoRes = True
        else:
            tempLoRes = False
        # print("mainLoRes", tempLoRes, type(tempLoRes))
        if tempLoRes:
            localresource = createLocalResource(custConfig['LocResGroupName'], custConfig['LocResName'], custConfig['sourcePath'],custConfig['destinationPath'])
            # print("localRes", localresource)
        subscription = createSubscription(custConfig)
        # print("subscription", subscription)
        updateconfig = gg.update_group_certificate_configuration(
            CertificateExpiryInMilliseconds='2592000000',
            GroupId=group['Id']
        )
        # 
        if tempLoRes:
            group_ver = gg.create_group_version(
                GroupId=group['Id'],
                CoreDefinitionVersionArn=core_definition['LatestVersionArn'],
                FunctionDefinitionVersionArn=gglambda['LatestVersionArn'],
                ResourceDefinitionVersionArn= localresource['LatestVersionArn'],
                SubscriptionDefinitionVersionArn=subscription['LatestVersionArn']
            )
        else:
            group_ver = gg.create_group_version(
                GroupId=group['Id'],
                CoreDefinitionVersionArn=core_definition['LatestVersionArn'],
                FunctionDefinitionVersionArn=gglambda['LatestVersionArn'],
                SubscriptionDefinitionVersionArn=subscription['LatestVersionArn']
            )  

        # SAVE created entities to the file.
        # You'll thank me for that when it's time to clean things up.
        if tempLoRes:
            state = {
                'group': group,
                'core_thing': core_thing,
                'keys_cert': keys_cert,
                'group_ver': group_ver,
                'core_definition': core_definition,
                'policy': policy,
                'localresource': localresource,
                'lambda': gglambda,
                'subscription': subscription,
                'Config Update': updateconfig
            }
        else:
             state = {
                'group': group,
                'core_thing': core_thing,
                'keys_cert': keys_cert,
                'group_ver': group_ver,
                'core_definition': core_definition,
                'policy': policy,
                'lambda': gglambda,
                'subscription': subscription,
                'Config Update': updateconfig
            }    
    
        with open('./state.json', 'w') as f:
            json.dump(state, f, indent=4)

        tempIoTHost = 'a1uto1ic4nrwqv.iot.' + region_name + '.amazonaws.com'
        tempGGHost = 'greengrass.iot.' + region_name + '.amazonaws.com'

        with open('./iot-pem-crt', 'w') as f:
            f.write(keys_cert['certificatePem'])

        with open('./iot-pem-key', 'w') as f:
            f.write(keys_cert['keyPair']['PrivateKey'])

        config = {
            "coreThing": {
                "caPath": "root.ca.pem",
                "certPath": "iot-pem-crt",
                "keyPath": "iot-pem-key",
                "thingArn": core_thing['thingArn'],
                "iotHost": tempIoTHost,
                "ggHost": tempGGHost,
                "keepAlive" : 600
            },
            "runtime": {
                "cgroup": {
                    "useSystemd": "yes"
                }
            },
            "managedRespawn": False
        }
        with open('./config.json', 'w') as f:
            json.dump(config, f, indent=4)
        #Deploy greengrass group
        deployResp = gg.create_deployment(
            DeploymentType="NewDeployment",
            GroupId=group['Id'],
            GroupVersionId=group_ver['Version']
        )
        print("Deployment Information", deployResp)
        # Create IoT Analytics Components
        createIoTA()
    else:
        print "This is not a valid lambda"    
else:
    print "We do not have a greengrass config file"
