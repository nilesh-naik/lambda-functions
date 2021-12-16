## About
Lambda function to delete a server from Chef after it is removed from autoscaling group.

## Tools and Services Used
- Python 3
- [boto3](https://github.com/boto/boto3)
- [requests](https://docs.python-requests.org/en/latest/)
- [chef](https://pypi.org/project/PyChef/)
- [logging](https://docs.python.org/3/library/logging.html)
- AWS Lambda
- AWS IAM
- AWS Cloudwatch
- AWS EC2 Autoscaling

## Usage
- Create deployment package with source code and dependencies. 
- Setup Lambda function with above package.
- Setup Cloudwatch rule to trigger function on notification.