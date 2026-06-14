from dotenv import load_dotenv
load_dotenv()

import boto3
import os

dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])

# Test Table 1: Write + Read memory
print('Testing devops-ai-memory...')
table1 = dynamodb.Table('devops-ai-memory')
table1.put_item(Item={
    'session_id': 'test-user#test-channel',
    'timestamp': 1234567890,
    'question': 'How do we roll back?',
    'answer': 'Use kubectl rollout undo',
    'ttl': 9999999999
})
result = table1.get_item(Key={
    'session_id': 'test-user#test-channel',
    'timestamp': 1234567890
})
print(f"devops-ai-memory works: {result['Item']['question']}")

# Test Table 2: Write + Read incident
print()
print('Testing devops-ai-incidents...')
table2 = dynamodb.Table('devops-ai-incidents')
table2.put_item(Item={
    'error_code': 'DB-502',
    'timestamp': 1234567890,
    'summary': 'Connection pool exhausted',
    'resolution': 'Kill idle connections'
})
result = table2.get_item(Key={
    'error_code': 'DB-502',
    'timestamp': 1234567890
})
print(f"devops-ai-incidents works: {result['Item']['summary']}")

print()
print('Both tables ready!')
