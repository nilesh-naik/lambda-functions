## About
Lambda function to send notifications of Codepipeline status change using EventBridge.

## Tools and Services Used
- Python 3
- [boto3](https://github.com/boto/boto3)
- [os](https://docs.python.org/3/library/os.html) 
- [requests](https://docs.python-requests.org/en/latest/)
- Webhook
- AWS KMS
- AWS Lambda
- AWS IAM
- AWS Cloudwatch
- AWS Codepipeline
- AWS EventBridge

## Usage
- Create webhook in Slack.
- Create deployment package with source code and dependencies. 
- Setup Lambda function with above package.
- Setup Cloudwatch rule to trigger function when pipelines state changes.