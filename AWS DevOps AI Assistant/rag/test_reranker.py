# test_reranker.py

from rag.reranker import BedrockReranker
from dotenv import load_dotenv
load_dotenv()


docs = [
    {
        "text": "IAC-5512 project between Microsoft and EY",
        "metadata": {"title": "IAC-5512"}
    },
    {
        "text": "IBM is a technology company",
        "metadata": {"title": "IBM"}
    }
]

reranker = BedrockReranker()

result = reranker.rerank(
    question="What is IAC-5512?",
    documents=docs
)

print(result)