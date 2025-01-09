# src/app.py
import os
import uuid
import json
import boto3
from typing import Dict, Any, Optional, List

# 環境変数 AWS_REGION がセットされていれば使う。なければ ap-northeast-1 をデフォルトに
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(os.environ['AWS_STACK_NAME'] + '-items')

def validate_item(item: Any) -> bool:
    """Validate the item data.
       テストで、引数が dict 以外の場合は AttributeError を期待しているので、ここで型チェックを行う。
    """
    if not isinstance(item, dict):
        raise AttributeError("Input must be a dictionary")

    required_fields = ['name', 'description']
    return all(field in item for field in required_fields)


def create_item(body: Any) -> Dict[str, Any]:
    """Create a new item
    
    テスト要件:
      - body が dict 以外なら AttributeError
      - validate_item() で必須フィールド不備なら ValueError
    """
    if not isinstance(body, dict):
        raise AttributeError("Item data must be a dictionary")

    if not validate_item(body):
        raise ValueError("Invalid item data. Required fields: name, description")

    item_id = str(uuid.uuid4())
    item = {
        'id': item_id,
        **body
    }
    
    try:
        table.put_item(Item=item)
    except boto3.exceptions.Boto3Error as e:
        # TODO: Implement retry logic if needed
        raise Exception(f"Failed to create item: {str(e)}")

    return item


def get_item(item_id: Any) -> Optional[Dict[str, Any]]:
    """
    Get an item by ID.

    テスト要件:
      - item_id が文字列以外のときに TypeError を期待するテストあり
    """
    if not isinstance(item_id, str):
        raise TypeError("Item ID must be a string")

    response = table.get_item(Key={'id': item_id})
    return response.get('Item')


def list_items(limit: Any = 100, last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    List items with pagination.

    テスト要件:
      - limit が int 以外なら TypeError
      - limit <= 0 なら ValueError
    """
    if not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    scan_kwargs = {'Limit': limit}
    if last_evaluated_key:
        scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
    
    response = table.scan(**scan_kwargs)
    return {
        'items': response.get('Items', []),
        'last_evaluated_key': response.get('LastEvaluatedKey')
    }


def update_item(item_id: Any, body: Any) -> Optional[Dict[str, Any]]:
    """
    Update an item.

    テスト要件:
      - item_id が文字列以外なら AttributeError
      - body が dict 以外なら AttributeError
      - validate_item() 失敗時は ValueError
    """
    if not isinstance(item_id, str):
        raise AttributeError("Item ID must be a string")

    if not isinstance(body, dict):
        raise AttributeError("Body must be a dictionary")

    if not validate_item(body):
        raise ValueError("Invalid item data")

    item = {
        'id': item_id,
        **body
    }
    
    try:
        table.put_item(Item=item)
    except Exception as e:
        # Databaseエラー等
        raise e
    return item


def delete_item(item_id: Any) -> None:
    """
    Delete an item.

    テスト要件:
      - item_id が文字列以外なら AttributeError
      - 空文字なら ValueError
      - 該当itemが無ければ ValueError
    """
    if not isinstance(item_id, str):
        raise AttributeError("Item ID must be a string")

    if not item_id:
        raise ValueError("Item ID is required (non-empty).")

    existing_item = get_item(item_id)
    if existing_item:
        table.delete_item(Key={'id': item_id})
    else:
        raise ValueError(f"Item with id {item_id} not found")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler"""
    # httpMethod が無い場合 KeyError となるが、テスト側でそれを想定するケースあり
    http_method = event['httpMethod']
    path_parameters = event.get('pathParameters', {})

    try:
        if http_method == 'POST':
            # JSON デコード時に失敗 → "Invalid JSON" メッセージを返すために分けてキャッチ
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return {'statusCode': 400, 'body': json.dumps({'message': 'Invalid JSON'})}

            item = create_item(body)
            return {'statusCode': 201, 'body': json.dumps(item)}

        elif http_method == 'GET':
            if path_parameters and 'id' in path_parameters:
                item_id = path_parameters['id']
                item = get_item(item_id)
                if not item:
                    return {'statusCode': 404, 'body': json.dumps({'message': 'Item not found'})}
                return {'statusCode': 200, 'body': json.dumps(item)}
            else:
                items = list_items()
                return {'statusCode': 200, 'body': json.dumps(items)}

        elif http_method == 'PUT':
            if not path_parameters or 'id' not in path_parameters:
                return {'statusCode': 400, 'body': json.dumps({'message': 'Missing item ID'})}
            
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return {'statusCode': 400, 'body': json.dumps({'message': 'Invalid JSON'})}

            item = update_item(path_parameters['id'], body)
            # update_item が None を返すケースを念のためチェック
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

    except json.JSONDecodeError:
        # 万が一ここまで落ちてきた場合の保険（POST/PUTの body=json.loads 以外から投げられたときなど）
        return {'statusCode': 400, 'body': json.dumps({'message': 'Invalid JSON'})}
    except ValueError as e:
        # 期待しているエラー文をそのまま返す
        return {'statusCode': 400, 'body': json.dumps({'message': str(e)})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal server error'})}
