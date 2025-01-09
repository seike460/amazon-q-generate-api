import json
import os
import pytest
from unittest.mock import patch, MagicMock
from src.app import (
    lambda_handler,
    validate_item,
    create_item,
    get_item,
    list_items,
    update_item,
    delete_item,
)

# Mock DynamoDB table for testing
@pytest.fixture
def mock_table():
    with patch('src.app.table') as mock:
        yield mock

# Test data
TEST_ITEM = {
    'name': 'Test Item',
    'description': 'Test Description'
}

TEST_ITEM_WITH_ID = {
    'id': 'test-id',
    'name': 'Test Item',
    'description': 'Test Description'
}

def test_validate_item_valid():
    assert validate_item(TEST_ITEM) is True

def test_validate_item_invalid():
    invalid_item = {'name': 'Test Item'}  # Missing description
    assert validate_item(invalid_item) is False

def test_create_item(mock_table):
    mock_table.put_item.return_value = {}
    result = create_item(TEST_ITEM)
    assert 'id' in result
    assert result['name'] == TEST_ITEM['name']
    assert result['description'] == TEST_ITEM['description']
    mock_table.put_item.assert_called_once()

def test_get_item(mock_table):
    mock_table.get_item.return_value = {'Item': TEST_ITEM_WITH_ID}
    result = get_item('test-id')
    assert result == TEST_ITEM_WITH_ID
    mock_table.get_item.assert_called_with(Key={'id': 'test-id'})

def test_list_items(mock_table):
    mock_table.scan.return_value = {'Items': [TEST_ITEM_WITH_ID]}
    result = list_items()
    assert result == [TEST_ITEM_WITH_ID]
    mock_table.scan.assert_called_once()

def test_update_item(mock_table):
    mock_table.put_item.return_value = {}
    result = update_item('test-id', TEST_ITEM)
    assert result['id'] == 'test-id'
    assert result['name'] == TEST_ITEM['name']
    assert result['description'] == TEST_ITEM['description']
    mock_table.put_item.assert_called_once()

def test_delete_item(mock_table):
    delete_item('test-id')
    mock_table.delete_item.assert_called_with(Key={'id': 'test-id'})

def test_lambda_handler_create():
    event = {
        'httpMethod': 'POST',
        'body': json.dumps(TEST_ITEM)
    }
    with patch('src.app.create_item') as mock_create:
        mock_create.return_value = TEST_ITEM_WITH_ID
        response = lambda_handler(event, {})
        assert response['statusCode'] == 201
        assert json.loads(response['body']) == TEST_ITEM_WITH_ID

def test_lambda_handler_get():
    event = {
        'httpMethod': 'GET',
        'pathParameters': {'id': 'test-id'}
    }
    with patch('src.app.get_item') as mock_get:
        mock_get.return_value = TEST_ITEM_WITH_ID
        response = lambda_handler(event, {})
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == TEST_ITEM_WITH_ID

def test_lambda_handler_list():
    event = {
        'httpMethod': 'GET'
    }
    with patch('src.app.list_items') as mock_list:
        mock_list.return_value = [TEST_ITEM_WITH_ID]
        response = lambda_handler(event, {})
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == [TEST_ITEM_WITH_ID]

def test_lambda_handler_update():
    event = {
        'httpMethod': 'PUT',
        'pathParameters': {'id': 'test-id'},
        'body': json.dumps(TEST_ITEM)
    }
    with patch('src.app.update_item') as mock_update:
        mock_update.return_value = TEST_ITEM_WITH_ID
        response = lambda_handler(event, {})
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == TEST_ITEM_WITH_ID

def test_lambda_handler_delete():
    event = {
        'httpMethod': 'DELETE',
        'pathParameters': {'id': 'test-id'}
    }
    with patch('src.app.delete_item') as mock_delete:
        response = lambda_handler(event, {})
        assert response['statusCode'] == 204