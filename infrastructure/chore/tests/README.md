# Tests

Basic unit tests for the chore CLI tool.

## Running Tests

Run all tests:

```bash
cd infrastructure/chore
python -m unittest discover tests
```

Run specific test:

```bash
python -m unittest tests.test_config
python -m unittest tests.test_ip_validation
```

## Test Coverage

Current test coverage:

- Configuration parsing (parameter overrides)
- IP validation and normalization

## Future Tests

Additional tests to be added:

- AWS client mocking (using moto or botocore.stub)
- Command validation
- Shell command execution
- Interactive mode navigation

## Mocking AWS Services

For AWS service tests, use one of:

1. **moto** - Mock AWS services
   ```bash
   pip install moto[all]
   ```

2. **botocore.stub** - Built-in boto3 stubbing
   ```python
   from botocore.stub import Stubber
   ```

Example with Stubber:

```python
import boto3
from botocore.stub import Stubber
from chore.core.aws import AWSClient

def test_get_stack():
    client = AWSClient()
    
    with Stubber(client.cfn) as stubber:
        stubber.add_response(
            'describe_stacks',
            {
                'Stacks': [{
                    'StackName': 'test-stack',
                    'StackStatus': 'CREATE_COMPLETE',
                }]
            }
        )
        
        stack = client.get_stack('test-stack')
        assert stack['StackName'] == 'test-stack'
```

