import json
import yaml
import boto3

region_name = 'us-east-1'
 
session = boto3.session.Session(region_name=region_name)

# gg = boto3.client('greengrass', region_name='us-east-1')
# iot = boto3.client('iot', region_name='us-east-1')

gg = boto3.client('greengrass', region_name=region_name)
iot = boto3.client('iot', region_name=region_name)


group = gg.create_group(Name="SS_IoTPipeline")

keys_cert = iot.create_keys_and_certificate(setAsActive=True)
core_thing = iot.create_thing(thingName="SS_IoTPipeline_core")

iot.attach_thing_principal(
    thingName=core_thing['thingName'],
    principal=keys_cert['certificateArn'])

core_policy_doc = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["iot:Publish", "iot:Subscribe", "iot:Connect", "iot:Receive", "iot:GetThingShadow", "iot:DeleteThingShadow", "iot:UpdateThingShadow"],
            # "Resource": ["arn:aws:iot:" + boto3.session.Session().region_name + ":*:*"]
            "Resource": ["arn:aws:iot:" + region_name + ":*:*"]
        },
        {
            "Effect": "Allow",
            "Action": ["greengrass:AssumeRoleForGroup", "greengrass:CreateCertificate", "greengrass:GetConnectivityInfo", "greengrass:GetDeployment", "greengrass:GetDeploymentArtifacts", "greengrass:UpdateConnectivityInfo", "greengrass:UpdateCoreDeploymentStatus"],
            "Resource": ["*"]
        }
    ]
}
policy = iot.create_policy(
    policyName="SS_IoTPipeline_policy",
    policyDocument=json.dumps(core_policy_doc))

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

# core_ver = gg.create_core_definition_version(
#     AmznClientToken='string',
#     CoreDefinitionId='string',
#     Cores=[
#         {
#             'CertificateArn': keys_cert['certificateArn'],
#             'Id': core_thing['thingId'],
#             'SyncShadow': True,
#             'ThingArn': core_thing['thingArn']
#         }
#     ]
# )

group_ver = gg.create_group_version(
    GroupId=group['Id'],
    # CoreDefinitionVersionArn=core_ver['Arn']
    CoreDefinitionVersionArn=core_definition['LatestVersionArn']
)

# SAVE created entities to the file.
# You'll thank me for that when it's time to clean things up.
state = {
    'group': group,
    'core_thing': core_thing,
    'keys_cert': keys_cert,
    'group_ver': group_ver,
    'core_definition': core_definition,
    'policy': policy
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