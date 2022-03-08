# MIT License

# Copyright (c) 2021 Martin Macecek

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json, boto3, logging, time, os
import cfnresponse

levels = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warn': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG
}
logger = logging.getLogger()
try:
    logger.setLevel(levels.get(os.getenv('LOG_LEVEL', 'info').lower()))
except KeyError as e:
    logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("event: %s", event)
    rp = event['ResourceProperties']
    rt = event['RequestType']
    rest = event['ResourceType']
    lri = event['LogicalResourceId']
    rv = {}
    try:
        if rest == 'Custom::DeleteBucketContent':
            delete_bucket_content(rp, rt)
        elif rest == 'Custom::CloudWatchDestination':
            cloudwatch_destinations(rp, rt)
        elif rest == 'Custom::GetHostedZoneId':
            rv = get_hosted_zone_id(rp, rt)
        else:
            logger.warning("No implementation for resourceType: %s", rest)
        cfnresponse.send(event, context, cfnresponse.SUCCESS, rv, lri)
    except Exception as ex:
        logger.error("Exception: %s", ex)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, lri)

def delete_bucket_content(rp, rt):
    bucket = rp['BucketName']
    logger.debug("bucket: %s, requestType: %s", bucket, rt)
    if rt == 'Delete':
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket)
        time.sleep(60)
        bucket.objects.all().delete()
        bucket.object_versions.all().delete()

def get_all_regions():
    return list(map(lambda e: e['RegionName'], filter(lambda e: e['RegionName'] != 'ap-northeast-3', boto3.client('ec2').describe_regions()['Regions'])))

def delete_cloudwatch_destinations(destinationName, regions):
    for r in regions:
        cw = boto3.client('logs', region_name=r)
        try:
            cw.delete_destination(destinationName=destinationName)
        except cw.exceptions.ResourceNotFoundException:
            logger.debug("Destination %s does not exist in %s.", destinationName, r)

def create_cloudwatch_destinations(regions, destinationName, roleArn, kinesisStreamArn, spokeAccounts):
    for r in regions:
        cw = boto3.client('logs', region_name=r)
        d = cw.put_destination(destinationName=destinationName, targetArn=kinesisStreamArn, roleArn=roleArn)['destination']
        accessPolicy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'AllowSpokesSubscribe',
                'Effect': 'Allow',
                'Principal': {
                    'AWS': spokeAccounts
                },
                'Action': 'logs:PutSubscriptionFilter',
                'Resource': d['arn']
            }]
        }
        cw.put_destination_policy(destinationName=destinationName, accessPolicy= json.dumps(accessPolicy))

def cloudwatch_destinations(rp, rt):
    allRegions = get_all_regions()
    if rt == 'Create' or rt == 'Update':
        regions = allRegions if rp['Regions'] else rp['Regions']
        if all(r in regions for r in allRegions):
            delete_cloudwatch_destinations(rp['DestinationName'], regions)
            create_cloudwatch_destinations(regions, rp['DestinationName'], rp['RoleArn'], rp['DataStreamArn'], rp['SpokeAccounts'])

    if rt == 'Delete':
        delete_cloudwatch_destinations(rp['DestinationName'], allRegions)

def get_hosted_zone_id(rp, rt):
    rv = {}
    if rt != 'Delete':
        dn = rp['DnsName']
        r53 = boto3.client('route53')
        r = r53.list_hosted_zones_by_name(DNSName=dn)
        hzi = r['HostedZones'][0]['Id'].split("/")[-1]
        logger.debug("Hosted zone ID: %s", hzi)
        rv = {"HostedZoneId": hzi}
    return rv
