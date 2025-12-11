"""
Custom resource handler for setting API Gateway HTTP API v2 resource policies.
HTTP API Gateway v2 doesn't support resource policies via CloudFormation directly,
so we use a custom resource Lambda to set it via the Management API.
"""

import json
import boto3
import urllib3

http = urllib3.PoolManager()

apigateway = boto3.client('apigatewayv2')


def handler(event, context):
    """
    Custom resource handler for API Gateway resource policy.
    
    Event structure:
    {
        "RequestType": "Create" | "Update" | "Delete",
        "ResponseURL": "...",
        "StackId": "...",
        "RequestId": "...",
        "ResourceType": "...",
        "LogicalResourceId": "...",
        "PhysicalResourceId": "...",
        "ResourceProperties": {
            "ApiId": "...",
            "VpcEndpointId": "...",
            "VpcCidrBlock": "..."
        }
    }
    """
    request_type = event['RequestType']
    api_id = event['ResourceProperties']['ApiId']
    vpc_endpoint_id = event['ResourceProperties']['VpcEndpointId']
    vpc_cidr = event['ResourceProperties']['VpcCidrBlock']
    
    physical_resource_id = f"{api_id}-resource-policy"
    
    try:
        if request_type in ['Create', 'Update']:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "execute-api:Invoke",
                        "Resource": f"arn:aws:execute-api:*:*:{api_id}/*/*",
                        "Condition": {
                            "StringNotEquals": {
                                "aws:SourceVpce": vpc_endpoint_id
                            }
                        }
                    },
                    {
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "execute-api:Invoke",
                        "Resource": f"arn:aws:execute-api:*:*:{api_id}/*/*",
                        "Condition": {
                            "StringNotLike": {
                                "aws:SourceIp": f"{vpc_cidr}/*"
                            }
                        }
                    },
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "execute-api:Invoke",
                        "Resource": f"arn:aws:execute-api:*:*:{api_id}/*/*",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceVpce": vpc_endpoint_id
                            }
                        }
                    }
                ]
            }
            
            apigateway.put_resource_policy(
                ApiId=api_id,
                ResourcePolicy=json.dumps(policy)
            )
            
            send_response(event, context, "SUCCESS", {
                "PhysicalResourceId": physical_resource_id
            })
            
        elif request_type == 'Delete':
            try:
                apigateway.delete_resource_policy(ApiId=api_id)
            except Exception as e:
                if 'NotFoundException' in str(type(e).__name__) or 'not found' in str(e).lower():
                    pass
                else:
                    raise
            
            send_response(event, context, "SUCCESS", {
                "PhysicalResourceId": physical_resource_id
            })
            
    except Exception as e:
        print(f"Error: {str(e)}")
        send_response(event, context, "FAILED", {
            "PhysicalResourceId": physical_resource_id
        }, reason=str(e))


def send_response(event, context, response_status, response_data, reason=None):
    """Send response to CloudFormation."""
    response_body = {
        'Status': response_status,
        'Reason': reason or f'See the details in CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': response_data.get('PhysicalResourceId', context.log_stream_name),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }
    
    json_response_body = json.dumps(response_body)
    
    response = http.request(
        'PUT',
        event['ResponseURL'],
        body=json_response_body.encode('utf-8'),
        headers={'Content-Type': '', 'Content-Length': str(len(json_response_body))}
    )
    
    return response

