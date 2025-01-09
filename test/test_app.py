from botocore.exceptions import ClientError
from moto import mock_dynamodb
from src.app import create_item
from src.app import create_item, table
from src.app import create_item, validate_item
from src.app import delete_item
from src.app import delete_item, get_item
from src.app import get_item
from src.app import lambda_handler
from src.app import list_items
from src.app import update_item
from src.app import update_item, validate_item
from src.app import validate_item
from typing import Dict, Any
from unittest.mock import patch
from unittest.mock import patch, MagicMock
import boto3
import json
import os
import pytest
import src.app
import uuid

class TestApp:

    @pytest.fixture
    def mock_get_item(self):
        with patch('src.app.get_item') as mock:
            yield mock

    @pytest.fixture
    def mock_table(self):
        with patch('src.app.table') as mock:
            yield mock

    def test_create_item_database_error(self, mock_table):
        """
        Test create_item when database operation fails
        """
        mock_table.put_item.side_effect = boto3.exceptions.Boto3Error("Database error")
        
        with pytest.raises(Exception, match="Failed to create item: Database error"):
            create_item({"name": "Test Item", "description": "Test Description"})

    def test_create_item_empty_input(self, mock_table):
        """
        Test create_item with empty input
        """
        with pytest.raises(ValueError, match="Invalid item data. Required fields: name, description"):
            create_item({})

    @mock_dynamodb
    def test_create_item_invalid_data(self):
        """
        Test create_item function with invalid data (missing required fields)
        """
        # Set up mock DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-items'
        os.environ['AWS_STACK_NAME'] = 'test'
        
        # Create mock table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )

        # Test invalid item data
        invalid_item = {'description': 'Test description'}
        
        with pytest.raises(ValueError) as exc_info:
            create_item(invalid_item)
        
        assert str(exc_info.value) == "Invalid item data. Required fields: name, description"

        # Clean up
        table.delete()
        del os.environ['AWS_STACK_NAME']

    def test_create_item_invalid_input_type(self, mock_table):
        """
        Test create_item with invalid input type
        """
        with pytest.raises(AttributeError):
            create_item("Not a dictionary")

    def test_create_item_missing_required_field(self, mock_table):
        """
        Test create_item with missing required field
        """
        with pytest.raises(ValueError, match="Invalid item data. Required fields: name, description"):
            create_item({"name": "Test Item"})

    @mock_dynamodb
    def test_create_item_valid_data(self):
        """
        Test creating an item with valid data.
        """
        # Set up mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-items',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )

        # Mock the environment variable
        os.environ['AWS_STACK_NAME'] = 'test'

        # Prepare test data
        item_data = {
            'name': 'Test Item',
            'description': 'This is a test item'
        }

        # Call the create_item function
        result = create_item(item_data)

        # Assert the result
        assert 'id' in result
        assert result['name'] == 'Test Item'
        assert result['description'] == 'This is a test item'

        # Verify the item was added to the table
        response = table.get_item(Key={'id': result['id']})
        assert 'Item' in response
        assert response['Item'] == result

    def test_create_item_with_empty_string_values(self, mock_table):
        """
        Test create_item with empty string values
        """
        item = {
            "name": "",
            "description": ""
        }
        result = create_item(item)
        
        assert "id" in result
        assert result["name"] == ""
        assert result["description"] == ""
        mock_table.put_item.assert_called_once()

    def test_create_item_with_extra_fields(self, mock_table):
        """
        Test create_item with extra fields in input
        """
        item = {
            "name": "Test Item",
            "description": "Test Description",
            "extra_field": "Extra Value"
        }
        result = create_item(item)
        
        assert "id" in result
        assert result["name"] == "Test Item"
        assert result["description"] == "Test Description"
        assert result["extra_field"] == "Extra Value"
        mock_table.put_item.assert_called_once()

    def test_create_item_with_very_long_values(self, mock_table):
        """
        Test create_item with very long string values
        """
        long_string = "a" * 1000000  # 1 million characters
        item = {
            "name": long_string,
            "description": long_string
        }
        result = create_item(item)
        
        assert "id" in result
        assert result["name"] == long_string
        assert result["description"] == long_string
        mock_table.put_item.assert_called_once()

    @patch('src.app.get_item')
    @patch('src.app.table')
    def test_delete_item_existing(self, mock_table, mock_get_item):
        """
        Test deleting an existing item successfully
        """
        # Arrange
        item_id = "test-item-id"
        mock_get_item.return_value = {"id": item_id, "name": "Test Item"}
        mock_delete_item = MagicMock()
        mock_table.delete_item = mock_delete_item

        # Act
        delete_item(item_id)

        # Assert
        mock_get_item.assert_called_once_with(item_id)
        mock_delete_item.assert_called_once_with(Key={'id': item_id})

    @patch('src.app.get_item')
    def test_delete_item_non_existing(self, mock_get_item):
        """
        Test deleting a non-existing item raises ValueError
        """
        # Arrange
        item_id = "non-existing-id"
        mock_get_item.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match=f"Item with id {item_id} not found"):
            delete_item(item_id)

        mock_get_item.assert_called_once_with(item_id)

    @patch('src.app.get_item')
    def test_delete_item_raises_value_error_when_item_not_found(self, mock_get_item):
        """
        Test that delete_item raises a ValueError when the item does not exist
        """
        # Arrange
        mock_get_item.return_value = None
        non_existent_item_id = "non_existent_id"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            delete_item(non_existent_item_id)

        assert str(exc_info.value) == f"Item with id {non_existent_item_id} not found"
        mock_get_item.assert_called_once_with(non_existent_item_id)

    def test_delete_item_with_boto3_error(self, mock_table, mock_get_item):
        """
        Test delete_item when a Boto3 error occurs.
        """
        mock_get_item.return_value = {"id": "test_id"}
        mock_table.delete_item.side_effect = ClientError(
            error_response={"Error": {"Code": "InternalServerError"}},
            operation_name="DeleteItem"
        )
        with pytest.raises(ClientError):
            delete_item("test_id")

    def test_delete_item_with_empty_input(self, mock_table, mock_get_item):
        """
        Test delete_item with empty input.
        """
        with pytest.raises(ValueError):
            delete_item("")

    def test_delete_item_with_invalid_type(self, mock_table, mock_get_item):
        """
        Test delete_item with an invalid input type.
        """
        with pytest.raises(AttributeError):
            delete_item(123)

    def test_delete_item_with_non_existent_id(self, mock_table, mock_get_item):
        """
        Test delete_item with a non-existent item ID.
        """
        mock_get_item.return_value = None
        with pytest.raises(ValueError, match="Item with id non_existent_id not found"):
            delete_item("non_existent_id")

    def test_delete_item_with_unicode_id(self, mock_table, mock_get_item):
        """
        Test delete_item with a Unicode item ID.
        """
        unicode_id = "ünicode_id"
        mock_get_item.return_value = {"id": unicode_id}
        delete_item(unicode_id)
        mock_table.delete_item.assert_called_once_with(Key={'id': unicode_id})

    @patch('src.app.table')
    def test_get_item_returns_existing_item(self, mock_table):
        """
        Test that get_item returns an existing item when it's found in the table.
        """
        # Arrange
        mock_item = {'id': '123', 'name': 'Test Item', 'description': 'This is a test item'}
        mock_response = {'Item': mock_item}
        mock_table.get_item.return_value = mock_response

        # Act
        result = get_item('123')

        # Assert
        assert result == mock_item
        mock_table.get_item.assert_called_once_with(Key={'id': '123'})

    @patch('src.app.table')
    def test_get_item_returns_none_for_nonexistent_item(self, mock_table):
        """
        Test that get_item returns None when the item is not found in the table.
        """
        # Arrange
        mock_table.get_item.return_value = {}

        # Act
        result = get_item('456')

        # Assert
        assert result is None
        mock_table.get_item.assert_called_once_with(Key={'id': '456'})

    def test_get_item_with_boto3_client_error(self, mock_table):
        """
        Test get_item function when a boto3 ClientError is raised.
        """
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'GetItem'
        )
        with pytest.raises(ClientError):
            get_item("some_id")

    def test_get_item_with_empty_input(self, mock_table):
        """
        Test get_item function with an empty input string.
        """
        mock_table.get_item.return_value = {}
        result = get_item("")
        assert result is None
        mock_table.get_item.assert_called_once_with(Key={'id': ''})

    def test_get_item_with_invalid_input(self, mock_table):
        """
        Test get_item function with an invalid input (non-string).
        """
        with pytest.raises(TypeError):
            get_item(123)

    def test_get_item_with_nonexistent_id(self, mock_table):
        """
        Test get_item function with a nonexistent item ID.
        """
        mock_table.get_item.return_value = {}
        result = get_item("nonexistent_id")
        assert result is None
        mock_table.get_item.assert_called_once_with(Key={'id': 'nonexistent_id'})

    def test_get_item_with_unexpected_response(self, mock_table):
        """
        Test get_item function when an unexpected response is received.
        """
        mock_table.get_item.return_value = {'UnexpectedKey': 'UnexpectedValue'}
        result = get_item("some_id")
        assert result is None
        mock_table.get_item.assert_called_once_with(Key={'id': 'some_id'})

    def test_get_item_with_very_long_id(self, mock_table):
        """
        Test get_item function with an extremely long item ID.
        """
        long_id = "a" * 1000  # Create a string with 1000 'a' characters
        mock_table.get_item.return_value = {}
        result = get_item(long_id)
        assert result is None
        mock_table.get_item.assert_called_once_with(Key={'id': long_id})

    def test_lambda_handler_1(self):
        """
        Test lambda_handler for POST request with valid data.
        Expects a successful item creation and 201 status code.
        """
        # Arrange
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'name': 'Test Item',
                'description': 'This is a test item'
            })
        }
        context = {}
        
        mock_item = {
            'id': '123456',
            'name': 'Test Item',
            'description': 'This is a test item'
        }
        
        # Act
        with patch('src.app.create_item', return_value=mock_item):
            response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 201
        assert json.loads(response['body']) == mock_item

    def test_lambda_handler_3(self):
        """
        Test GET request for an existing item by ID
        """
        # Arrange
        mock_item = {"id": "456", "name": "Another Test Item", "description": "This is another test item"}
        
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'id': '456'}
        }
        context = {}

        # Act
        with patch('src.app.get_item', return_value=mock_item):
            response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == mock_item

    def test_lambda_handler_5(self):
        """
        Test lambda_handler with PUT method and no pathParameters
        """
        # Arrange
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({'name': 'Test Item', 'description': 'Test Description'})
        }
        context = {}

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'message': 'Missing item ID'}

    def test_lambda_handler_7(self):
        """
        Test lambda_handler with DELETE method and missing item ID in pathParameters
        """
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {}
        }
        context = {}

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'message': 'Missing item ID'}

    def test_lambda_handler_8(self):
        """
        Test successful deletion of an item using DELETE method
        """
        # Arrange
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {'id': '123456'}
        }
        context = {}

        # Act
        with patch('src.app.delete_item') as mock_delete_item:
            mock_delete_item.return_value = None
            response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 204
        mock_delete_item.assert_called_once_with('123456')

    @patch('src.app.delete_item')
    def test_lambda_handler_delete_item_success(self, mock_delete_item):
        """
        Test successful deletion of an item using DELETE method
        """
        # Arrange
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {'id': '123456'}
        }
        context = {}
        mock_delete_item.return_value = None

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 204
        mock_delete_item.assert_called_once_with('123456')

    def test_lambda_handler_delete_missing_id(self):
        """
        Test lambda_handler with DELETE method and missing item ID
        """
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': None
        }
        context = {}

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'message': 'Missing item ID'}

    def test_lambda_handler_delete_missing_id_2(self):
        """
        Test lambda_handler DELETE request with missing item ID
        """
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {}
        }
        result = lambda_handler(event, None)
        assert result['statusCode'] == 400
        assert json.loads(result['body'])['message'] == 'Missing item ID'

    @patch('src.app.list_items')
    def test_lambda_handler_get_all_items(self, mock_list_items):
        """
        Test lambda_handler when GET request is made without a specific item ID.
        Should return all items.
        """
        # Arrange
        mock_items = {'items': [{'id': '1', 'name': 'Item 1'}, {'id': '2', 'name': 'Item 2'}]}
        mock_list_items.return_value = mock_items
        event = {
            'httpMethod': 'GET',
            'pathParameters': None
        }
        context = {}

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == mock_items
        mock_list_items.assert_called_once()

    @patch('src.app.get_item')
    def test_lambda_handler_get_existing_item(self, mock_get_item):
        """
        Test GET request for an existing item by ID
        """
        # Arrange
        mock_item = {"id": "123", "name": "Test Item", "description": "This is a test item"}
        mock_get_item.return_value = mock_item
        
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'id': '123'}
        }
        context = {}

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == mock_item
        mock_get_item.assert_called_once_with('123')

    @patch('src.app.get_item')
    def test_lambda_handler_get_item_not_found(self, mock_get_item):
        """
        Test lambda_handler when GET request is made for a non-existent item.
        """
        # Arrange
        mock_get_item.return_value = None
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'id': 'non_existent_id'}
        }
        context = {}

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 404
        assert json.loads(response['body']) == {'message': 'Item not found'}
        mock_get_item.assert_called_once_with('non_existent_id')

    def test_lambda_handler_get_nonexistent_item(self):
        """
        Test lambda_handler GET request for a non-existent item
        """
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'id': 'non-existent-id'}
        }
        result = lambda_handler(event, None)
        assert result['statusCode'] == 404
        assert json.loads(result['body'])['message'] == 'Item not found'

    def test_lambda_handler_internal_server_error(self):
        """
        Test lambda_handler internal server error handling
        """
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'id': 'test-id'}
        }
        # Mock the get_item function to raise an exception
        def mock_get_item(item_id):
            raise Exception("Simulated internal error")
        
        original_get_item = src.app.get_item
        src.app.get_item = mock_get_item

        try:
            result = lambda_handler(event, None)
            assert result['statusCode'] == 500
            assert json.loads(result['body'])['message'] == 'Internal server error'
        finally:
            # Restore the original function
            src.app.get_item = original_get_item

    def test_lambda_handler_invalid_http_method(self):
        """
        Test lambda_handler with an invalid HTTP method
        """
        event = {
            'httpMethod': 'INVALID',
            'pathParameters': {},
            'body': '{}'
        }
        result = lambda_handler(event, None)
        assert result['statusCode'] == 405
        assert json.loads(result['body'])['message'] == 'Method not allowed'

    def test_lambda_handler_invalid_json_body(self):
        """
        Test lambda_handler with invalid JSON body
        """
        event = {
            'httpMethod': 'POST',
            'body': 'invalid json'
        }
        result = lambda_handler(event, None)
        assert result['statusCode'] == 400
        assert 'Invalid JSON' in json.loads(result['body'])['message']

    def test_lambda_handler_method_not_allowed(self):
        """
        Test lambda_handler with an unsupported HTTP method.
        Expects a 405 Method Not Allowed response.
        """
        # Arrange
        event = {
            'httpMethod': 'PATCH',  # An unsupported method
            'pathParameters': {},
            'body': '{}'
        }
        context = {}

        # Act
        result = lambda_handler(event, context)

        # Assert
        assert result['statusCode'] == 405
        assert json.loads(result['body']) == {'message': 'Method not allowed'}

    def test_lambda_handler_missing_http_method(self):
        """
        Test lambda_handler with missing HTTP method
        """
        event = {
            'pathParameters': {},
            'body': '{}'
        }
        with pytest.raises(KeyError):
            lambda_handler(event, None)

    def test_lambda_handler_missing_required_fields(self):
        """
        Test lambda_handler with missing required fields in POST request
        """
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'name': 'Test Item'})  # Missing 'description'
        }
        result = lambda_handler(event, None)
        assert result['statusCode'] == 400
        assert 'Invalid item data' in json.loads(result['body'])['message']

    def test_lambda_handler_post_success(self):
        """
        Test lambda_handler for POST request with valid data.
        Expects a successful item creation and 201 status code.
        """
        # Arrange
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'name': 'Test Item',
                'description': 'This is a test item'
            })
        }
        context = {}
        
        mock_item = {
            'id': '123456',
            'name': 'Test Item',
            'description': 'This is a test item'
        }
        
        # Act
        with patch('src.app.create_item', return_value=mock_item):
            response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 201
        assert json.loads(response['body']) == mock_item

    @patch('src.app.update_item')
    def test_lambda_handler_put_item_not_found(self, mock_update_item):
        """
        Test lambda_handler with PUT request when item is not found
        """
        # Arrange
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'non_existent_id'},
            'body': json.dumps({'name': 'Updated Item', 'description': 'Updated Description'})
        }
        context = {}
        mock_update_item.return_value = None

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 404
        assert json.loads(response['body']) == {'message': 'Item not found'}
        mock_update_item.assert_called_once_with('non_existent_id', {'name': 'Updated Item', 'description': 'Updated Description'})

    def test_lambda_handler_put_missing_id(self):
        """
        Test lambda_handler with PUT method and missing item ID
        """
        # Arrange
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {},
            'body': json.dumps({'name': 'Test Item', 'description': 'Test Description'})
        }
        context = {}

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'message': 'Missing item ID'}

    def test_lambda_handler_put_missing_id_2(self):
        """
        Test lambda_handler PUT request with missing item ID
        """
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {},
            'body': json.dumps({'name': 'Updated Item', 'description': 'Updated Description'})
        }
        result = lambda_handler(event, None)
        assert result['statusCode'] == 400
        assert json.loads(result['body'])['message'] == 'Missing item ID'

    def test_list_items_2(self):
        """
        Test list_items function without a last_evaluated_key
        """
        # Mock the DynamoDB table
        mock_table = MagicMock()
        mock_response = {
            'Items': [{'id': '1', 'name': 'Item 1'}, {'id': '2', 'name': 'Item 2'}],
            'LastEvaluatedKey': {'id': '2'}
        }
        mock_table.scan.return_value = mock_response

        # Patch the table in the app module
        with patch('src.app.table', mock_table):
            result = list_items()

        # Assert the function returns the expected structure
        assert 'items' in result
        assert 'last_evaluated_key' in result

        # Assert the items are returned correctly
        assert result['items'] == mock_response['Items']

        # Assert the LastEvaluatedKey is returned correctly
        assert result['last_evaluated_key'] == mock_response['LastEvaluatedKey']

        # Assert that scan was called with the correct parameters
        mock_table.scan.assert_called_once_with(Limit=100)

    @patch('src.app.table')
    def test_list_items_with_boto3_error(self, mock_table):
        """Test list_items when boto3 raises an exception."""
        mock_table.scan.side_effect = boto3.exceptions.Boto3Error("Boto3 error")
        with pytest.raises(Exception) as exc_info:
            list_items()
        assert str(exc_info.value) == "Boto3 error"

    @patch('src.app.table')
    def test_list_items_with_empty_response(self, mock_table):
        """Test list_items when the DynamoDB response is empty."""
        mock_table.scan.return_value = {}
        result = list_items()
        assert result == {'items': [], 'last_evaluated_key': None}

    @patch('src.app.table')
    def test_list_items_with_invalid_last_evaluated_key(self, mock_table):
        """Test list_items with an invalid last_evaluated_key."""
        mock_table.scan.side_effect = boto3.exceptions.Boto3Error("Invalid ExclusiveStartKey")
        with pytest.raises(Exception) as exc_info:
            list_items(last_evaluated_key={"invalid_key": "value"})
        assert str(exc_info.value) == "Invalid ExclusiveStartKey"

    @patch('src.app.table')
    def test_list_items_with_large_limit(self, mock_table):
        """Test list_items with a very large limit value."""
        mock_table.scan.return_value = {'Items': []}
        result = list_items(limit=1000000)
        mock_table.scan.assert_called_once_with(Limit=1000000)
        assert result == {'items': [], 'last_evaluated_key': None}

    @patch('src.app.table')
    def test_list_items_with_last_evaluated_key(self, mock_table):
        """
        Test list_items function with a last_evaluated_key provided
        """
        # Arrange
        limit = 50
        last_evaluated_key = {'id': 'last_item_id'}
        mock_response = {
            'Items': [{'id': 'item1'}, {'id': 'item2'}],
            'LastEvaluatedKey': {'id': 'item2'}
        }
        mock_table.scan.return_value = mock_response

        # Act
        result = list_items(limit=limit, last_evaluated_key=last_evaluated_key)

        # Assert
        mock_table.scan.assert_called_once_with(Limit=limit, ExclusiveStartKey=last_evaluated_key)
        assert result == {
            'items': [{'id': 'item1'}, {'id': 'item2'}],
            'last_evaluated_key': {'id': 'item2'}
        }

    @patch('src.app.table')
    def test_list_items_with_negative_limit(self, mock_table):
        """Test list_items with a negative limit value."""
        with pytest.raises(ValueError):
            list_items(limit=-1)

    @patch('src.app.table')
    def test_list_items_with_non_integer_limit(self, mock_table):
        """Test list_items with a non-integer limit value."""
        with pytest.raises(TypeError):
            list_items(limit="100")

    @patch('src.app.table')
    def test_list_items_with_zero_limit(self, mock_table):
        """Test list_items with a zero limit value."""
        with pytest.raises(ValueError):
            list_items(limit=0)

    def test_update_item_database_error(self, mock_table):
        """
        Test update_item when a database error occurs
        """
        mock_table.put_item.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            update_item("test_id", {"name": "Test Item", "description": "Test Description"})

    def test_update_item_empty_input(self, mock_table):
        """
        Test update_item with empty input
        """
        with pytest.raises(ValueError, match="Invalid item data"):
            update_item("test_id", {})

    def test_update_item_extra_fields(self, mock_table):
        """
        Test update_item with extra fields in the input
        """
        item = update_item("test_id", {"name": "Test Item", "description": "Test Description", "extra": "Extra Field"})
        assert "extra" in item
        mock_table.put_item.assert_called_once()

    def test_update_item_invalid_id_type(self, mock_table):
        """
        Test update_item with invalid id type
        """
        with pytest.raises(AttributeError):
            update_item(123, {"name": "Test Item", "description": "Test Description"})

    def test_update_item_invalid_input_type(self, mock_table):
        """
        Test update_item with invalid input type
        """
        with pytest.raises(AttributeError):
            update_item("test_id", "invalid_input")

    def test_update_item_missing_required_fields(self, mock_table):
        """
        Test update_item with missing required fields
        """
        with pytest.raises(ValueError, match="Invalid item data"):
            update_item("test_id", {"name": "Test Item"})

    @patch('src.app.validate_item', return_value=True)
    @patch('src.app.table')
    def test_update_item_returns_updated_item(self, mock_table, mock_validate_item):
        """
        Test that update_item returns the updated item
        """
        # Arrange
        item_id = "test-id"
        body = {
            "name": "Updated Item",
            "description": "This is an updated item"
        }
        mock_table.put_item = MagicMock()

        # Act
        result = update_item(item_id, body)

        # Assert
        assert result == {"id": item_id, **body}
        mock_validate_item.assert_called_once_with(body)
        mock_table.put_item.assert_called_once_with(Item={"id": item_id, **body})

    @patch('src.app.table')
    def test_update_item_with_dynamodb_error(self, mock_table):
        """
        Test updating an item when DynamoDB raises an error
        """
        # Arrange
        item_id = "test-id"
        body = {
            "name": "Test Item",
            "description": "This is a test item"
        }
        mock_table.put_item.side_effect = Exception("DynamoDB error")

        # Act & Assert
        with pytest.raises(Exception, match="DynamoDB error"):
            update_item(item_id, body)

    def test_update_item_with_invalid_data(self):
        """
        Test updating an item with invalid data
        """
        # Arrange
        item_id = "test-id"
        body = {
            "name": "Test Item"
            # Missing 'description' field
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid item data"):
            update_item(item_id, body)

    @patch('src.app.table')
    def test_update_item_with_valid_data(self, mock_table):
        """
        Test updating an item with valid data
        """
        # Arrange
        item_id = "test-id"
        body = {
            "name": "Test Item",
            "description": "This is a test item"
        }
        mock_table.put_item = MagicMock()

        # Act
        result = update_item(item_id, body)

        # Assert
        assert result == {"id": item_id, **body}
        mock_table.put_item.assert_called_once_with(Item={"id": item_id, **body})

    def test_validate_item_empty_input(self):
        """
        Test validate_item with empty input
        """
        assert not validate_item({})

    def test_validate_item_empty_values(self):
        """
        Test validate_item with empty values for required fields
        """
        assert validate_item({'name': '', 'description': ''})

    def test_validate_item_extra_fields(self):
        """
        Test validate_item with extra fields
        """
        assert validate_item({'name': 'Test Item', 'description': 'Test Description', 'extra': 'Extra Field'})

    def test_validate_item_incorrect_type(self):
        """
        Test validate_item with incorrect input type
        """
        with pytest.raises(AttributeError):
            validate_item(None)
        
        with pytest.raises(AttributeError):
            validate_item("Not a dictionary")

    def test_validate_item_missing_required_fields(self):
        """
        Test validate_item with missing required fields
        """
        assert not validate_item({'name': 'Test Item'})
        assert not validate_item({'description': 'Test Description'})

    def test_validate_item_non_string_values(self):
        """
        Test validate_item with non-string values for required fields
        """
        assert validate_item({'name': 123, 'description': True})

    def test_validate_item_with_empty_dict(self):
        """
        Test that validate_item returns False when the item is an empty dictionary
        """
        item: Dict[str, Any] = {}
        assert validate_item(item) == False

    def test_validate_item_with_extra_fields(self):
        """
        Test that validate_item returns True when all required fields are present,
        even if there are extra fields
        """
        item: Dict[str, Any] = {
            'name': 'Test Item',
            'description': 'This is a test item',
            'extra_field': 'Extra information'
        }
        assert validate_item(item) == True

    def test_validate_item_with_missing_fields(self):
        """
        Test that validate_item returns False when required fields are missing
        """
        item: Dict[str, Any] = {
            'name': 'Test Item'
        }
        assert validate_item(item) == False

    def test_validate_item_with_valid_data(self):
        """
        Test that validate_item returns True when all required fields are present
        """
        item: Dict[str, Any] = {
            'name': 'Test Item',
            'description': 'This is a test item'
        }
        assert validate_item(item) == True