# rag/retriever.py

from vectorstore.opensearch_client import OpenSearchVectorStore
from embeddings.bedrock_embeddings import BedrockEmbeddings
from rag.reranker import BedrockReranker
from typing import List, Dict


class HybridRetriever:
    """
    Hybrid Retriever

    Combines:
    1. Dense Vector Search
    2. BM25 Keyword Search

    Then:
    - Merge
    - Deduplicate
    - Re-rank
    """

    def __init__(self, k: int = 8):
        self.vs = OpenSearchVectorStore()
        self.embedder = BedrockEmbeddings()
        self.reranker = BedrockReranker()
        self.k = k

    def retrieve(self, query: str) -> List[Dict]:

        print("\n" + "=" * 80)
        print("[HYBRID] RETRIEVAL START")
        print("=" * 80)
        print(f"[HYBRID] Query: {query}")

        # =====================================================
        # VECTOR SEARCH
        # =====================================================

        query_emb = self.embedder.embed_query(query)

        vector_results = self.vs.similarity_search(
            query_embedding=query_emb,
            k=self.k * 2,
        )

        print(
            f"[HYBRID] Vector Results: "
            f"{len(vector_results)}"
        )

        # =====================================================
        # BM25 SEARCH
        # =====================================================

        bm25_results = self.vs.bm25_search(
            query_text=query,
            k=self.k * 2,
        )

        print(
            f"[HYBRID] BM25 Results: "
            f"{len(bm25_results)}"
        )

        # =====================================================
        # MERGE RESULTS
        # =====================================================

        all_results = vector_results + bm25_results

        print(
            f"[HYBRID] Combined Results: "
            f"{len(all_results)}"
        )

        # =====================================================
        # SORT BY SCORE
        # =====================================================

        all_results = sorted(
            all_results,
            key=lambda x: x["score"],
            reverse=True,
        )

        # =====================================================
        # DEDUPLICATE BY URL
        # =====================================================

        seen_urls = set()
        deduped = []

        for result in all_results:

            url = result["metadata"].get(
                "url",
                ""
            )

            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append(result)

        print(
            f"[HYBRID] Deduped Results: "
            f"{len(deduped)}"
        )

        # =====================================================
        # RERANKING
        # =====================================================

        print("\n")
        print("=" * 80)
        print("[RERANK] START")
        print("=" * 80)

        reranked = self.reranker.rerank(
            question=query,
            documents=deduped[:10]
        )

        for idx, r in enumerate(
            reranked,
            start=1
        ):

            print(
                f"{idx}. "
                f"{r['metadata'].get('title', 'Unknown')} "
                f"| rerank_score="
                f"{r.get('rerank_score', 0)}"
            )

        print("=" * 80)
        print("[RERANK] END")
        print("=" * 80)

        print("=" * 80)
        print("[HYBRID] RETRIEVAL END")
        print("=" * 80)

        return reranked[:self.k]

    def format_context(
        self,
        results: List[Dict],
    ) -> str:

        parts = []

        for i, r in enumerate(
            results,
            start=1
        ):

            meta = r["metadata"]

            source = (
                meta.get("title")
                or meta.get("key")
                or meta.get("url", "Unknown")
            )

            parts.append(
                f"[{i}] Source: {source}\n"
                f"URL: {meta.get('url', '')}\n"
                f"Score: {round(r.get('score', 0), 4)}\n"
                f"Rerank Score: {r.get('rerank_score', 'N/A')}\n"
                f"Content:\n{r['text']}\n"
            )

        return "\n---\n".join(parts)