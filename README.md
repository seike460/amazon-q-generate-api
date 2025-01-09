# Serverless CRUD API with AWS Lambda and DynamoDB

This project implements a serverless CRUD (Create, Read, Update, Delete) API using AWS Lambda, API Gateway, and DynamoDB. It provides a robust backend for managing items with a RESTful interface.

The API allows users to perform operations on items stored in a DynamoDB table. It's built using Python and the AWS Serverless Application Model (SAM) for easy deployment and management.

Key features include:
- RESTful API endpoints for CRUD operations
- Serverless architecture using AWS Lambda
- Data persistence with Amazon DynamoDB
- Input validation and error handling
- Automated testing suite

## Repository Structure

```
.
├── src
│   └── app.py
├── template.yaml
└── test
    └── test_app.py
```

- `src/app.py`: Main application code containing Lambda handler and CRUD operations
- `template.yaml`: AWS SAM template defining the serverless infrastructure
- `test/test_app.py`: Test suite for the application

## Usage Instructions

### Prerequisites

- Python 3.12
- AWS CLI configured with appropriate permissions
- AWS SAM CLI

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Deployment

1. Build the SAM application:
   ```
   sam build
   ```

2. Deploy the application:
   ```
   sam deploy --guided
   ```

   Follow the prompts to configure your deployment settings.

### API Endpoints

- Create Item: `POST /items`
- Get Item: `GET /items/{id}`
- List Items: `GET /items`
- Update Item: `PUT /items/{id}`
- Delete Item: `DELETE /items/{id}`

### Example Usage

Creating an item:

```python
import requests
import json

api_url = "https://<api-id>.execute-api.<region>.amazonaws.com/Prod"

item = {
    "name": "Example Item",
    "description": "This is an example item"
}

response = requests.post(f"{api_url}/items", json=item)
print(response.json())
```

### Testing

Run the test suite:

```
pytest test/test_app.py
```

### Troubleshooting

1. Issue: API returns 500 Internal Server Error
   - Check CloudWatch Logs for the Lambda function
   - Verify DynamoDB table permissions

2. Issue: Items not persisting in DynamoDB
   - Ensure the DynamoDB table name in `template.yaml` matches the one used in `app.py`
   - Verify the Lambda function has the correct IAM permissions

For detailed logs:
1. Open the AWS CloudWatch console
2. Navigate to Log groups
3. Find the log group for your Lambda function (usually `/aws/lambda/<function-name>`)
4. Check the most recent log stream for error messages

## Data Flow

The request data flow through the application follows these steps:

1. Client sends HTTP request to API Gateway endpoint
2. API Gateway triggers the corresponding Lambda function
3. Lambda function processes the request:
   - Validates input data
   - Performs CRUD operation on DynamoDB
   - Handles any errors
4. Lambda function returns response to API Gateway
5. API Gateway sends HTTP response back to the client

```
Client <-> API Gateway <-> Lambda <-> DynamoDB
```

## Infrastructure

The project uses AWS SAM to define and deploy the following resources:

- DynamoDB Table:
  - Name: `<stack-name>-items`
  - Partition Key: `id` (String)
  - On-demand billing
  - Server-side encryption enabled
  - Point-in-time recovery enabled

- Lambda Function:
  - Name: `CrudFunction`
  - Runtime: Python 3.12
  - Handler: `app.lambda_handler`
  - Environment Variables:
    - `AWS_STACK_NAME`: References the CloudFormation stack name
  - IAM Permissions: DynamoDB CRUD policy for the items table
  - API Gateway Events:
    - POST /items
    - GET /items/{id}
    - GET /items
    - PUT /items/{id}
    - DELETE /items/{id}

- API Gateway:
  - Implicitly created by SAM to handle HTTP requests

The infrastructure is defined in the `template.yaml` file, which can be deployed using the AWS SAM CLI.