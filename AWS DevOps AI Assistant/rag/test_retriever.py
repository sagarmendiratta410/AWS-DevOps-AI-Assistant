# File: test_retriever.py (create this at project root)

from dotenv import load_dotenv
load_dotenv()

import os
from rag.retriever import HybridRetriever

print("=" * 70)
print("TESTING RETRIEVER.PY")
print("=" * 70)
print()

# Test 1: Check environment variables
print("Step 1: Checking environment variables...")
try:
    os.environ['OPENSEARCH_ENDPOINT']
    os.environ['OPENSEARCH_INDEX']
    os.environ['BEDROCK_EMBED_MODEL_ID']
    print("✓ All required env vars found")
except KeyError as e:
    print(f"✗ Missing env var: {e}")
    exit(1)

print()

# Test 2: Initialize retriever
print("Step 2: Initializing HybridRetriever...")
try:
    retriever = HybridRetriever(k=8)
    print("✓ Retriever initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize: {e}")
    exit(1)

print()

# Test 3: Test embedding
print("Step 3: Testing embeddings...")
try:
    test_query = "How do we roll back a deployment?"
    query_emb = retriever.embedder.embed_query(test_query)
    print(f"✓ Query embedded successfully")
    print(f"  Embedding dimension: {len(query_emb)}")
except Exception as e:
    print(f"✗ Embedding failed: {e}")
    exit(1)

print()

# Test 4: Test retrieval
print("Step 4: Retrieving similar chunks from OpenSearch...")
try:
    results = retriever.retrieve(test_query)
    print(f"✓ Retrieval successful")
    print(f"  Found {len(results)} results")
except Exception as e:
    print(f"✗ Retrieval failed: {e}")
    exit(1)

print()

# Test 5: Show results
print("Step 5: Formatting and displaying results...")
if len(results) == 0:
    print("⚠ No results found! Your question might not match any docs.")
    print("  Try asking about: Kubernetes, Lambda, Database, Error codes, etc.")
else:
    print(f"Found {len(results)} relevant chunks:\n")
    
    for i, r in enumerate(results, 1):
        meta = r['metadata']
        print(f"[{i}] {meta.get('title', 'Unknown')}")
        print(f"    Source: {meta.get('source', 'unknown')}")
        print(f"    Score: {r['score']:.4f}")
        print(f"    URL: {meta.get('url', 'N/A')}")
        print(f"    Text preview: {r['text'][:100]}...")
        print()

print()

# Test 6: Format context (what will be sent to Nova)
print("Step 6: Formatted context (for Amazon Nova):")
print("-" * 70)
context = retriever.format_context(results)
print(context[:500])  # First 500 chars
if len(context) > 500:
    print("\n... [truncated] ...\n")
print("-" * 70)

print()
print("=" * 70)
print("✓ RETRIEVER TEST COMPLETE")
print("=" * 70)