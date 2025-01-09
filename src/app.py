import json
import os
import uuid
import boto3
from typing import Dict, Any, Optional, List

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['AWS_STACK_NAME'] + '-items')


def validate_item(item: Dict[str, Any]) -> bool:
    """Validate the item data"""
    required_fields = ['name', 'description']
    return all(field in item for field in required_fields)


def create_item(body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new item"""
    if not validate_item(body):
        raise ValueError(f"Invalid item data. Required fields: {', '.join(['name', 'description'])}")
    
    item_id = str(uuid.uuid4())
    item = {
        'id': item_id,
        **body
    }
    
    try:
        table.put_item(Item=item)
    except boto3.exceptions.Boto3Error as e:
        # TODO: Implement retry logic
        raise Exception(f"Failed to create item: {str(e)}") # import boto3
    return item


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    """Get an item by ID"""
    response = table.get_item(Key={'id': item_id})
    return response.get('Item')


def list_items(limit: int = 100, last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """List items with pagination"""
    scan_kwargs = {
        'Limit': limit
    }
    if last_evaluated_key:
        scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
    
    response = table.scan(**scan_kwargs)
    return {
        'items': response.get('Items', []),
        'last_evaluated_key': response.get('LastEvaluatedKey')
    }


def update_item(item_id: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an item"""
    if not validate_item(body):
        raise ValueError("Invalid item data")
    
    item = {
        'id': item_id,
        **body
    }
    
    table.put_item(Item=item)
    return item


def delete_item(item_id: str) -> None:
    """Delete an item"""
    existing_item = get_item(item_id)
    if existing_item:
        table.delete_item(Key={'id': item_id})
    else:
        raise ValueError(f"Item with id {item_id} not found")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler"""
    http_method = event['httpMethod']
    path_parameters = event.get('pathParameters', {})
    
    try:
        # Handle different HTTP methods
        if http_method == 'POST':
            body = json.loads(event['body'])
            item = create_item(body)
            return {'statusCode': 201, 'body': json.dumps(item)}
            
        elif http_method == 'GET':
            if path_parameters and 'id' in path_parameters:
                item = get_item(path_parameters['id'])
                if not item:
                    return {'statusCode': 404, 'body': json.dumps({'message': 'Item not found'})}
                return {'statusCode': 200, 'body': json.dumps(item)}
            else:
                items = list_items()
                return {'statusCode': 200, 'body': json.dumps(items)}
                
        elif http_method == 'PUT':
            if not path_parameters or 'id' not in path_parameters:
                return {'statusCode': 400, 'body': json.dumps({'message': 'Missing item ID'})}
            body = json.loads(event['body'])
            item = update_item(path_parameters['id'], body)
            if not item:
                return {'statusCode': 404, 'body': json.dumps({'message': 'Item not found'})}
            return {'statusCode': 200, 'body': json.dumps(item)}
            
        elif http_method == 'DELETE':
            if not path_parameters or 'id' not in path_parameters:
                return {'statusCode': 400, 'body': json.dumps({'message': 'Missing item ID'})}
            delete_item(path_parameters['id'])
            return {'statusCode': 204}
            
        else:
            return {'statusCode': 405, 'body': json.dumps({'message': 'Method not allowed'})}
            
    except ValueError as e:
        return {'statusCode': 400, 'body': json.dumps({'message': str(e)})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal server error'})}