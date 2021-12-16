## About
Lambda function to schedule EC2 scale-in and scale-out policies based on external schedule.

## Tools and Services Used
- Python 3
- [boto3](https://github.com/boto/boto3)
- [requests](https://docs.python-requests.org/en/latest/)
- [datetime](https://docs.python.org/3/library/datetime.html)
- AWS Lambda
- AWS IAM
- AWS Cloudwatch
- AWS Secrets Manager
- AWS EC2 Autoscaling

## Usage
- Create deployment package with source code and dependencies. 
- Setup Lambda function with above package.
- Create secret in Secrets Manager to store application API key.
- Attach role to Lambda function to update autoscaling group and fetch secret from Secrets manager.
- Setup Cloudwatch rule to trigger function everyday.