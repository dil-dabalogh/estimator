"""AWS API wrapper utilities using boto3."""

import boto3
import time
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError
from rich.progress import Progress, SpinnerColumn, TextColumn
from chore.core.console import console, error, success, warning


class AWSClient:
    """Wrapper for AWS API operations."""
    
    def __init__(self, region: str = "us-west-2"):
        """Initialize AWS clients."""
        self.region = region
        self.cfn = boto3.client("cloudformation", region_name=region)
        self.lambda_client = boto3.client("lambda", region_name=region)
        self.logs = boto3.client("logs", region_name=region)
        self.s3 = boto3.client("s3", region_name=region)
        self.bedrock = boto3.client("bedrock-agent", region_name=region)
        self.iam = boto3.client("iam", region_name=region)
        self.sts = boto3.client("sts", region_name=region)
        self.tagging = boto3.client("resourcegroupstaggingapi", region_name=region)
    
    # CloudFormation operations
    
    def get_stack(self, stack_name: str) -> Optional[Dict[str, Any]]:
        """Get CloudFormation stack details."""
        try:
            response = self.cfn.describe_stacks(StackName=stack_name)
            return response["Stacks"][0] if response["Stacks"] else None
        except ClientError as e:
            if "does not exist" in str(e):
                return None
            raise
    
    def get_stack_output(self, stack_name: str, output_key: str) -> Optional[str]:
        """Get specific output value from stack."""
        stack = self.get_stack(stack_name)
        if not stack or "Outputs" not in stack:
            return None
        
        for output in stack["Outputs"]:
            if output["OutputKey"] == output_key:
                return output["OutputValue"]
        return None
    
    def get_stack_parameter(self, stack_name: str, parameter_key: str) -> Optional[str]:
        """Get specific parameter value from stack."""
        stack = self.get_stack(stack_name)
        if not stack or "Parameters" not in stack:
            return None
        
        for param in stack["Parameters"]:
            if param["ParameterKey"] == parameter_key:
                return param["ParameterValue"]
        return None
    
    def update_stack_parameters(
        self,
        stack_name: str,
        parameters: Dict[str, str],
        wait: bool = True,
    ) -> bool:
        """
        Update CloudFormation stack parameters.
        
        Args:
            stack_name: Name of the stack
            parameters: Dict of parameter key-value pairs to update
            wait: Whether to wait for update to complete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            stack = self.get_stack(stack_name)
            if not stack:
                error(f"Stack {stack_name} not found")
                return False
            
            param_list = []
            for key, value in parameters.items():
                param_list.append({
                    "ParameterKey": key,
                    "ParameterValue": value,
                })
            
            existing_params = stack.get("Parameters", [])
            for param in existing_params:
                key = param["ParameterKey"]
                if key not in parameters:
                    param_list.append({
                        "ParameterKey": key,
                        "UsePreviousValue": True,
                    })
            
            self.cfn.update_stack(
                StackName=stack_name,
                UsePreviousTemplate=True,
                Parameters=param_list,
                Capabilities=["CAPABILITY_IAM"],
            )
            
            if wait:
                success("Stack update initiated, waiting for completion...")
                return self.wait_for_stack_update(stack_name)
            
            return True
            
        except ClientError as e:
            error(f"Failed to update stack: {e}")
            return False
    
    def wait_for_stack_update(self, stack_name: str, timeout: int = 600) -> bool:
        """Wait for stack update to complete."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Waiting for stack update...", total=None)
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                stack = self.get_stack(stack_name)
                if not stack:
                    return False
                
                status = stack["StackStatus"]
                
                if status == "UPDATE_COMPLETE":
                    progress.update(task, description="Stack update completed")
                    return True
                elif "FAILED" in status or "ROLLBACK" in status:
                    progress.update(task, description=f"Stack update failed: {status}")
                    return False
                
                time.sleep(5)
            
            warning("Stack update timed out")
            return False
    
    # Lambda operations
    
    def get_lambda_config(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get Lambda function configuration."""
        try:
            return self.lambda_client.get_function_configuration(
                FunctionName=function_name
            )
        except ClientError:
            return None
    
    def get_lambda_logs(
        self,
        function_name: str,
        filter_pattern: str = "",
        limit: int = 50,
        minutes: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent Lambda logs."""
        log_group = f"/aws/lambda/{function_name}"
        start_time = int((time.time() - minutes * 60) * 1000)
        
        try:
            if filter_pattern:
                response = self.logs.filter_log_events(
                    logGroupName=log_group,
                    startTime=start_time,
                    filterPattern=filter_pattern,
                    limit=limit,
                )
            else:
                response = self.logs.filter_log_events(
                    logGroupName=log_group,
                    startTime=start_time,
                    limit=limit,
                )
            return response.get("events", [])
        except ClientError:
            return []
    
    # S3 operations
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if S3 bucket exists."""
        try:
            self.s3.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False
    
    def create_bucket(self, bucket_name: str) -> bool:
        """Create S3 bucket."""
        try:
            if self.region == "us-east-1":
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": self.region},
                )
            return True
        except ClientError as e:
            error(f"Failed to create bucket: {e}")
            return False
    
    def put_bucket_policy(self, bucket_name: str, policy: str) -> bool:
        """Apply bucket policy."""
        try:
            self.s3.put_bucket_policy(Bucket=bucket_name, Policy=policy)
            return True
        except ClientError as e:
            error(f"Failed to apply bucket policy: {e}")
            return False
    
    # Bedrock Agent operations
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get Bedrock Agent details."""
        try:
            response = self.bedrock.get_agent(agentId=agent_id)
            return response.get("agent")
        except ClientError:
            return None
    
    def prepare_agent(self, agent_id: str) -> bool:
        """Prepare Bedrock Agent."""
        try:
            self.bedrock.prepare_agent(agentId=agent_id)
            return True
        except ClientError as e:
            error(f"Failed to prepare agent: {e}")
            return False
    
    def wait_for_agent_prepared(self, agent_id: str, timeout: int = 120) -> bool:
        """Wait for agent to be in PREPARED state."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Preparing agent...", total=None)
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                agent = self.get_agent(agent_id)
                if not agent:
                    return False
                
                status = agent.get("agentStatus")
                
                if status == "PREPARED":
                    progress.update(task, description="Agent prepared")
                    return True
                elif status in ["FAILED", "DELETING"]:
                    progress.update(task, description=f"Agent preparation failed: {status}")
                    return False
                
                time.sleep(3)
            
            warning("Agent preparation timed out")
            return False
    
    # IAM operations
    
    def get_account_id(self) -> str:
        """Get AWS account ID."""
        return self.sts.get_caller_identity()["Account"]
    
    # Resource tagging operations
    
    def get_stack_resources(self, stack_name: str) -> List[Dict[str, Any]]:
        """
        Get all resources in a CloudFormation stack.
        
        Args:
            stack_name: Name of the CloudFormation stack
        
        Returns:
            List of resource dictionaries with ResourceType, PhysicalResourceId, and LogicalResourceId
        """
        try:
            resources = []
            paginator = self.cfn.get_paginator("list_stack_resources")
            
            for page in paginator.paginate(StackName=stack_name):
                for resource in page.get("StackResourceSummaries", []):
                    resources.append({
                        "LogicalResourceId": resource["LogicalResourceId"],
                        "PhysicalResourceId": resource.get("PhysicalResourceId", ""),
                        "ResourceType": resource["ResourceType"],
                        "ResourceStatus": resource.get("ResourceStatus", ""),
                    })
            
            return resources
        except ClientError as e:
            error(f"Failed to get stack resources: {e}")
            return []
    
    def get_resource_arns(self, stack_name: str) -> List[str]:
        """
        Get ARNs of all taggable resources in a CloudFormation stack.
        
        Args:
            stack_name: Name of the CloudFormation stack
        
        Returns:
            List of resource ARNs
        """
        resources = self.get_stack_resources(stack_name)
        arns = []
        
        for resource in resources:
            physical_id = resource.get("PhysicalResourceId", "")
            resource_type = resource.get("ResourceType", "")
            
            if not physical_id:
                continue
            
            # Construct ARN based on resource type
            if resource_type.startswith("AWS::Lambda::"):
                if not physical_id.startswith("arn:"):
                    arn = f"arn:aws:lambda:{self.region}:{self.get_account_id()}:function:{physical_id}"
                else:
                    arn = physical_id
                arns.append(arn)
            elif resource_type.startswith("AWS::DynamoDB::"):
                if not physical_id.startswith("arn:"):
                    arn = f"arn:aws:dynamodb:{self.region}:{self.get_account_id()}:table/{physical_id}"
                else:
                    arn = physical_id
                arns.append(arn)
            elif resource_type.startswith("AWS::ApiGatewayV2::"):
                if resource_type == "AWS::ApiGatewayV2::Api":
                    if not physical_id.startswith("arn:"):
                        arn = f"arn:aws:apigateway:{self.region}::/apis/{physical_id}"
                    else:
                        arn = physical_id
                    arns.append(arn)
            elif resource_type.startswith("AWS::IAM::"):
                if physical_id.startswith("arn:"):
                    arns.append(physical_id)
            elif physical_id.startswith("arn:"):
                arns.append(physical_id)
        
        return arns
    
    def tag_resources(self, resource_arns: List[str], tags: Dict[str, str]) -> Dict[str, Any]:
        """
        Apply tags to AWS resources.
        
        Args:
            resource_arns: List of resource ARNs to tag
            tags: Dictionary of tag key-value pairs
        
        Returns:
            Dictionary with 'successful' and 'failed' resource counts
        """
        if not resource_arns:
            return {"successful": 0, "failed": 0, "failed_resources": {}}
        
        result = {"successful": 0, "failed": 0, "failed_resources": {}}
        
        # AWS Resource Groups Tagging API allows up to 20 resources per call
        batch_size = 20
        
        for i in range(0, len(resource_arns), batch_size):
            batch = resource_arns[i:i + batch_size]
            
            try:
                response = self.tagging.tag_resources(
                    ResourceARNList=batch,
                    Tags=tags
                )
                
                # Check for partial failures
                failed_map = response.get("FailedResourcesMap", {})
                
                result["successful"] += len(batch) - len(failed_map)
                result["failed"] += len(failed_map)
                
                for arn, error_info in failed_map.items():
                    result["failed_resources"][arn] = error_info.get("ErrorMessage", "Unknown error")
                    
            except ClientError as e:
                error(f"Failed to tag batch: {e}")
                result["failed"] += len(batch)
                for arn in batch:
                    result["failed_resources"][arn] = str(e)
        
        return result
    
    def untag_resources(self, resource_arns: List[str], tag_keys: List[str]) -> Dict[str, Any]:
        """
        Remove tags from AWS resources.
        
        Args:
            resource_arns: List of resource ARNs to untag
            tag_keys: List of tag keys to remove
        
        Returns:
            Dictionary with 'successful' and 'failed' resource counts
        """
        if not resource_arns:
            return {"successful": 0, "failed": 0, "failed_resources": {}}
        
        result = {"successful": 0, "failed": 0, "failed_resources": {}}
        
        # AWS Resource Groups Tagging API allows up to 20 resources per call
        batch_size = 20
        
        for i in range(0, len(resource_arns), batch_size):
            batch = resource_arns[i:i + batch_size]
            
            try:
                response = self.tagging.untag_resources(
                    ResourceARNList=batch,
                    TagKeys=tag_keys
                )
                
                # Check for partial failures
                failed_map = response.get("FailedResourcesMap", {})
                
                result["successful"] += len(batch) - len(failed_map)
                result["failed"] += len(failed_map)
                
                for arn, error_info in failed_map.items():
                    result["failed_resources"][arn] = error_info.get("ErrorMessage", "Unknown error")
                    
            except ClientError as e:
                error(f"Failed to untag batch: {e}")
                result["failed"] += len(batch)
                for arn in batch:
                    result["failed_resources"][arn] = str(e)
        
        return result
    
    def get_resource_tags(self, resource_arn: str) -> Dict[str, str]:
        """
        Get tags for a specific resource.
        
        Args:
            resource_arn: ARN of the resource
        
        Returns:
            Dictionary of tag key-value pairs
        """
        try:
            response = self.tagging.get_resources(
                ResourceARNList=[resource_arn]
            )
            
            resources = response.get("ResourceTagMappingList", [])
            if resources:
                tags = resources[0].get("Tags", [])
                return {tag["Key"]: tag["Value"] for tag in tags}
            
            return {}
        except ClientError as e:
            error(f"Failed to get tags for resource: {e}")
            return {}


def get_aws_client(region: str = "us-west-2") -> AWSClient:
    """Get AWS client instance."""
    return AWSClient(region)

