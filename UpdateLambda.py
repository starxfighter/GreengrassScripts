import json
import yaml
import boto3
import os
import traceback
import sys

with open('state.json') as state:
    curState = json.load(state)
with open('uConfig.json') as f:
    uConfig = json.load(f)

gg = boto3.client('greengrass', region_name=uConfig['region'])
clientLambda = boto3.client('lambda', region_name=uConfig['region'])

oldLambda = curState['lambda']
print("oldlambda: {}".format(oldLambda))
oldFunId = oldLambda['Id']
print("old Id: {}".format(oldFunId))
oldGet = gg.get_function_definition(
    FunctionDefinitionId = oldFunId
)
odelete = gg.delete_function_definition(
    FunctionDefinitionId = oldGet['Id']
)
print("delete: {}".format(odelete))
tempARN = uConfig['lambdaARN'] + ':' + uConfig['lambdaAlias']
if uConfig['lambdaLongLived'] == "True":
    tempPinned = True
else:
    tempPinned = False
newLambda = gg.create_function_definition(
                Name=uConfig['lambdaFunName'],
                InitialVersion={
                    'Functions': [
                        {
                            'Id': uConfig['lambdaIdName'], 
                            'FunctionArn': tempARN,
                            'FunctionConfiguration': {
                                'Pinned': tempPinned,
                                'MemorySize': uConfig['lambdaMemSize'],
                                'Timeout': uConfig['lambdaTimeout'],
                                'Environment': {
                                    'AccessSysfs': False,
                                    'ResourceAccessPolicies': [
                                        {
                                            'ResourceId': uConfig['LocResName'],
                                            'Permission': 'rw'
                                        }
                                    ]
                                } 
                            }
                        }
                    ]
                }
            )
tempARN = uConfig['lambdaARN'] + ':' + uConfig['lambdaAlias']
subscription = gg.create_subscription_definition(
    InitialVersion={
        'Subscriptions': [
            {
                'Id': uConfig['subscriptionIdName'],
                'Source': tempARN,
                'Subject': uConfig['subscriptionSubject'],
                'Target': 'cloud'
            }
        ]
    },
    Name=uConfig['subscriptionName']
) 

localRes =  gg.create_resource_definition(
    Name= uConfig['LocResGroupName'],
    InitialVersion={
        'Resources': [
            {
                'Id': uConfig['LocResName'],
                'Name': 'TempDircetory',
                'ResourceDataContainer': {
                    'LocalVolumeResourceData': {
                        'SourcePath': uConfig['sourcePath'],
                        'DestinationPath': uConfig['destinationPath'],
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

group_ver = gg.create_group_version(
    GroupId=curState['group']['Id'],
    CoreDefinitionVersionArn=curState['core_definition']['LatestVersionArn'],
    FunctionDefinitionVersionArn=newLambda['LatestVersionArn'],
    ResourceDefinitionVersionArn= localRes['LatestVersionArn'],
    SubscriptionDefinitionVersionArn=subscription['LatestVersionArn']
)
deployResp = gg.create_deployment(
    DeploymentType="Redeployment",
    DeploymentId=curState['deployment']['DeploymentId'],
    GroupId=curState['group']['Id'],
    GroupVersionId=curState['group_ver']['Version']
)