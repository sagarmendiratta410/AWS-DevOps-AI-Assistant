import os

import boto3
from dotenv import load_dotenv 
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

load_dotenv()

def get_os_client() -> OpenSearch:
    session = boto3.Session(profile_name="default")
    credentials = session.get_credentials()

    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        os.environ["AWS_REGION"],
        "aoss",
        session_token=credentials.token,
    )

    return OpenSearch(
        hosts=[
            {
                "host": os.environ["OPENSEARCH_ENDPOINT"].replace(
                    "https://", ""
                ),
                "port": 443,
            }
        ],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )

INDEX_BODY = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512,
        }
    },
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16,
                    },
                },
            },
            "text": {"type": "text"},
            "source": {"type": "keyword"},
            "url": {"type": "keyword"},
            "title": {"type": "text"},
            "chunk_id": {"type": "keyword"},
            "last_modified": {"type": "date"},
        }
    },
}


def create_index() -> None:
    client = get_os_client()

    endpoint = os.environ["OPENSEARCH_ENDPOINT"]
    index_name = os.environ["OPENSEARCH_INDEX"]

    print("\n===== CONFIGURATION =====")
    print("Endpoint:", endpoint)
    print("Index:", index_name)
    print("AWS Region:", os.environ["AWS_REGION"])

    print("\n===== AWS IDENTITY =====")
    identity = boto3.client("sts").get_caller_identity()
    print(identity)

    print("\n===== OPENSEARCH INFO =====")
    try:
        info = client.info()
        print(info)
    except Exception as e:
        print("Could not retrieve cluster info:", e)

    print("\n===== CHECKING INDEX =====")
    exists = client.indices.exists(index=index_name)
    print(f"Index exists? {exists}")

    if not exists:
        print("\n===== CREATING INDEX =====")

        response = client.indices.create(
            index=index_name,
            body=INDEX_BODY,
        )

        print("Create response:")
        print(response)

    print("\n===== VERIFYING INDEX =====")
    exists_after = client.indices.exists(index=index_name)
    print(f"Index exists after create? {exists_after}")

    if exists_after:
        print("\n===== INDEX DETAILS =====")
        print(client.indices.get(index=index_name))

    print("\n===== ALL INDICES =====")

    try:
        indices = client.cat.indices(format="json")
        print(indices)
    except Exception as e:
        print("Could not list indices:", e)


if __name__ == "__main__":
    try:
        create_index()
        print("\nSUCCESS")
    except Exception as e:
        print("\nERROR")
        print(type(e).__name__)
        print(str(e))
        raise







'''
OUTPUT




===== CONFIGURATION =====
Endpoint: https://cslcjz673eyolzhitir6.aoss.us-east-1.on.aws
Index: devops-runbooks
AWS Region: us-east-1

===== AWS IDENTITY =====
{'UserId': 'AIDA4U72MLXGEEKVLDWWJ', 'Account': '869719104972', 'Arn': 'arn:aws:iam::869719104972:user/iam-admin-user', 'ResponseMetadata': {'RequestId': '3b4d46d1-1957-4cc2-a1e0-e4bceba6a750', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '3b4d46d1-1957-4cc2-a1e0-e4bceba6a750', 'x-amz-sts-extended-request-id': 'MTp1cy1lYXN0LTE6UzoxNzgwMzA3MDQ5MTA5Okc6Nm43aDNaZnM=', 'content-type': 'text/xml', 'content-length': '411', 'date': 'Mon, 01 Jun 2026 09:44:09 GMT'}, 'RetryAttempts': 0}}

===== OPENSEARCH INFO =====
Could not retrieve cluster info: NotFoundError(404, '')

===== CHECKING INDEX =====
Index exists? False

===== CREATING INDEX =====
Create response:
{'acknowledged': True, 'shards_acknowledged': False, 'index': 'devops-runbooks'}

===== VERIFYING INDEX =====
Index exists after create? True

===== INDEX DETAILS =====
{'devops-runbooks': {'aliases': {}, 'mappings': {'properties': {'chunk_id': {'type': 'keyword'}, 'embedding': {'type': 'knn_vector', 'dimension': 1536, 'method': {'engine': 'faiss', 'space_type': 'cosinesimil', 'name': 'hnsw', 'parameters': {'ef_construction': 512, 'm': 16}}, 'mode': 'on_disk', 'compression_level': '32x'}, 'last_modified': {'type': 'date'}, 'source': {'type': 'keyword'}, 'text': {'type': 'text'}, 'title': {'type': 'text'}, 'url': {'type': 'keyword'}}}, 'settings': {'index': {'knn.remote_index_build': {'enabled': 'true'}, 'number_of_shards': '2', 'knn.algo_param': {'ef_search': '512'}, 'provided_name': 'devops-runbooks', 'knn': 'true', 'creation_date': '1780307052646', 'custom_doc_id_enabled': 'true', 'number_of_replicas': '0', 'uuid': 'bhyRgp4BYxKGw-KYxxfL', 'version': {'created': '137247827'}}}}}

===== ALL INDICES =====
[{'health': '', 'status': 'OPEN', 'index': 'devops-runbooks', 'uuid': 'bhyRgp4BYxKGw-KYxxfL', 'pri': '', 'rep': '', 'docs.count': '0', 'docs.deleted': '0', 'store.size': '0b', 'pri.store.size': '0b'}]

SUCCESS

'''        