# DeploymentHelper
Helper for deployments of resources not fully supported by CloudFormation or when resources must be deployed conditionally

# Features
1. Deletion of bucket content on stack delete including all versions of objects
1. Creation of CloudWatch Destinations in specified regions and allowing access from defined spoke accounts
1. Get the hosted zone id based on the dns name. Useful in a lot of places in CloudFormation, where the hosted zone id is required, but the hosted zone itself is managed outside of your CFN tempate and hence you often only know the dns name.

# Usage
1. Deploy AWS Lambda function with this code (ideally as part of the CloudFormation Template you are deploying). Specify environmental variable LOG_LEVEL to set log level (critical, error, warn, info, debug) with info being default if unspecified.
