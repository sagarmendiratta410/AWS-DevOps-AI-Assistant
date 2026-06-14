# vectorstore/opensearch_client.py

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from vectorstore.index_manager import get_os_client

logger = logging.getLogger(__name__)


class OpenSearchVectorStore:
    def __init__(self):
        self.client = get_os_client()
        self.index = os.environ["OPENSEARCH_INDEX"]

    # =====================================================
    # UPSERT EMBEDDINGS
    # =====================================================

    def add_embeddings(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
    ) -> None:

        actions = []

        for text, emb, meta in zip(
            texts,
            embeddings,
            metadatas,
        ):

            doc_id = meta.get(
                "chunk_id",
                str(uuid.uuid4()),
            )

            actions.append(
                {
                    "index": {
                        "_index": self.index,
                        "_id": doc_id,
                    }
                }
            )

            actions.append(
                {
                    "text": text,
                    "embedding": emb,
                    **{
                        k: v
                        for k, v in meta.items()
                        if k != "chunk_id"
                    },
                }
            )

        self.client.bulk(body=actions)

        logger.info(
            f"[OpenSearch] Indexed {len(texts)} chunks"
        )

    # =====================================================
    # VECTOR SEARCH (KNN)
    # =====================================================

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 8,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        query = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": k,
                    }
                }
            },
            "_source": {
                "excludes": ["embedding"]
            },
        }

        if source_filter:
            query["query"] = {
                "bool": {
                    "must": [query["query"]],
                    "filter": [
                        {
                            "term": {
                                "source": source_filter
                            }
                        }
                    ],
                }
            }

        resp = self.client.search(
            index=self.index,
            body=query,
        )

        return [
            {
                "text": hit["_source"]["text"],
                "score": hit["_score"],
                "metadata": {
                    k: v
                    for k, v in hit["_source"].items()
                    if k != "text"
                },
            }
            for hit in resp["hits"]["hits"]
        ]

    # =====================================================
    # BM25 KEYWORD SEARCH
    # =====================================================

    def bm25_search(
        self,
        query_text: str,
        k: int = 8,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        query = {
            "size": k,
            "query": {
                "match": {
                    "text": query_text
                }
            },
            "_source": {
                "excludes": ["embedding"]
            },
        }

        if source_filter:
            query["query"] = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "text": query_text
                            }
                        }
                    ],
                    "filter": [
                        {
                            "term": {
                                "source": source_filter
                            }
                        }
                    ],
                }
            }

        resp = self.client.search(
            index=self.index,
            body=query,
        )

        return [
            {
                "text": hit["_source"]["text"],
                "score": hit["_score"],
                "metadata": {
                    k: v
                    for k, v in hit["_source"].items()
                    if k != "text"
                },
            }
            for hit in resp["hits"]["hits"]
        ]