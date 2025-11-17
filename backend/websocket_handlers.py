"""
WebSocket handlers for AWS API Gateway WebSocket API.
These handlers manage WebSocket connections via DynamoDB and API Gateway Management API.
"""

import os
import json
import boto3
from typing import Dict, Any

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE_NAME = os.environ.get('CONNECTIONS_TABLE', '')
connections_table = dynamodb.Table(CONNECTIONS_TABLE_NAME) if CONNECTIONS_TABLE_NAME else None


def connect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket $connect route.
    Stores connection ID and session ID in DynamoDB.
    """
    connection_id = event['requestContext']['connectionId']
    
    # Extract session ID from query string
    query_params = event.get('queryStringParameters') or {}
    session_id = query_params.get('sessionId', '')
    
    if not session_id:
        print(f"No sessionId provided for connection {connection_id}")
        return {
            'statusCode': 400,
            'body': 'Missing sessionId parameter'
        }
    
    # Store connection in DynamoDB
    try:
        if connections_table:
            connections_table.put_item(
                Item={
                    'connectionId': connection_id,
                    'sessionId': session_id,
                }
            )
        print(f"Connection {connection_id} established for session {session_id}")
    except Exception as e:
        print(f"Error storing connection: {e}")
        return {
            'statusCode': 500,
            'body': 'Failed to establish connection'
        }
    
    return {
        'statusCode': 200,
        'body': 'Connected'
    }


def disconnect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket $disconnect route.
    Removes connection ID from DynamoDB.
    """
    connection_id = event['requestContext']['connectionId']
    
    # Remove connection from DynamoDB
    try:
        if connections_table:
            connections_table.delete_item(
                Key={'connectionId': connection_id}
            )
        print(f"Connection {connection_id} disconnected")
    except Exception as e:
        print(f"Error removing connection: {e}")
    
    return {
        'statusCode': 200,
        'body': 'Disconnected'
    }


def default_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket $default route.
    Receives messages from clients (currently just keepalive).
    """
    connection_id = event['requestContext']['connectionId']
    
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'ping')
        
        print(f"Received message from {connection_id}: action={action}")
        
        # For now, just acknowledge the message
        # Real-time updates are sent via broadcast_to_session (called from worker)
        
    except Exception as e:
        print(f"Error handling message: {e}")
        return {
            'statusCode': 500,
            'body': 'Error processing message'
        }
    
    return {
        'statusCode': 200,
        'body': 'Message received'
    }


def broadcast_to_session(session_id: str, message: Dict[str, Any], api_gateway_endpoint: str):
    """
    Broadcast a message to all connections for a given session.
    This function is called by the worker to send updates to connected clients.
    
    Args:
        session_id: The session ID to broadcast to
        message: The message dict to send
        api_gateway_endpoint: The API Gateway management endpoint (e.g., https://xxx.execute-api.region.amazonaws.com/prod)
    """
    if not connections_table:
        print("Warning: CONNECTIONS_TABLE not configured")
        return
    
    try:
        # Query DynamoDB for all connections with this session ID
        response = connections_table.query(
            IndexName='sessionId-index',
            KeyConditionExpression='sessionId = :sid',
            ExpressionAttributeValues={':sid': session_id}
        )
        
        connections = response.get('Items', [])
        
        if not connections:
            print(f"No connections found for session {session_id}")
            return
        
        # Initialize API Gateway Management API client
        # Extract domain and stage from endpoint
        # endpoint format: https://xxxxx.execute-api.region.amazonaws.com/stage
        apigw_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=api_gateway_endpoint
        )
        
        message_data = json.dumps(message).encode('utf-8')
        
        # Send message to each connection
        for connection in connections:
            connection_id = connection['connectionId']
            try:
                apigw_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=message_data
                )
                print(f"Sent message to connection {connection_id}")
            except apigw_client.exceptions.GoneException:
                # Connection is stale, remove it
                print(f"Connection {connection_id} is gone, removing from table")
                connections_table.delete_item(
                    Key={'connectionId': connection_id}
                )
            except Exception as e:
                print(f"Error sending to {connection_id}: {e}")
    
    except Exception as e:
        print(f"Error broadcasting to session {session_id}: {e}")

