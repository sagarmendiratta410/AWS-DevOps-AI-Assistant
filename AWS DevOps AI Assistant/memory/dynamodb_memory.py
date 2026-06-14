import os
import time
import logging
from typing import List, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key


logger = logging.getLogger(__name__)


class DynamoDBMemory:
    """
    Two-table DynamoDB memory:
    1. Conversation history (session_id → recent messages)
    2. Incident resolutions (error_code → past fixes)
    """

    def __init__(self):
        ddb = boto3.resource(
            'dynamodb',
            region_name=os.environ['AWS_REGION']
        )
        self.memory_tbl = ddb.Table(os.environ['DYNAMODB_MEMORY_TABLE'])
        self.incidents_tbl = ddb.Table(os.environ['DYNAMODB_INCIDENTS_TABLE'])
        logger.info("[MEMORY] DynamoDBMemory initialized")

    # ─────────────────────────────────────────────────────────────────
    # Conversation Memory
    # ─────────────────────────────────────────────────────────────────

    def get_history(
        self,
        session_id: str,
        n: int = 10
    ) -> List[Dict]:
        """
        Load last n messages for a session.
        session_id format: user_id#channel_id
        """
        resp = self.memory_tbl.query(
            KeyConditionExpression=Key('session_id').eq(session_id),
            ScanIndexForward=False,  # newest first
            Limit=n
        )
        items = resp.get('Items', [])
        logger.info(f"[MEMORY] get_history | session={session_id} | found={len(items)}")
        return list(reversed(items))  # return oldest first

    def save_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        sources: List[str] = None
    ) -> None:
        """
        Save one Q&A turn to memory.
        Automatically expires after 7 days via TTL.
        """
        now = int(time.time())

        self.memory_tbl.put_item(
            Item={
                'session_id': session_id,
                'timestamp': now,
                'question': question,
                'answer': answer,
                'sources': sources or [],
                'ttl': now + 7 * 24 * 3600  # expire in 7 days
            }
        )
        logger.info(f"[MEMORY] save_turn | session={session_id}")

    def format_history(self, history: List[Dict]) -> str:
        """
        Format history into a readable string for the prompt.
        Only uses last 5 turns to keep context window small.
        """
        if not history:
            return 'No prior conversation.'

        lines = []
        for h in history[-5:]:  # last 5 turns only
            lines.append(f"Q: {h['question']}")
            lines.append(f"A: {h['answer'][:300]}...")  # truncate long answers
            lines.append("")  # blank line between turns

        return '\n'.join(lines)

    # ─────────────────────────────────────────────────────────────────
    # Incident Memory
    # ─────────────────────────────────────────────────────────────────

    def save_incident(
        self,
        error_code: str,
        description: str,
        resolution: str,
        runbook_url: str = None
    ) -> None:
        """
        Save an incident and its resolution for future reference.
        Example: error_code='DB-502', resolution='Kill idle connections'
        """
        self.incidents_tbl.put_item(
            Item={
                'error_code': error_code,
                'timestamp': int(time.time()),
                'description': description,
                'resolution': resolution,
                'runbook_url': runbook_url or ''
            }
        )
        logger.info(f"[MEMORY] save_incident | error_code={error_code}")

    def get_incident(self, error_code: str) -> Optional[Dict]:
        """
        Get the most recent resolution for an error code.
        Returns None if not found.
        """
        resp = self.incidents_tbl.query(
            KeyConditionExpression=Key('error_code').eq(error_code),
            ScanIndexForward=False,  # newest first
            Limit=1
        )
        items = resp.get('Items', [])
        result = items[0] if items else None
        logger.info(f"[MEMORY] get_incident | error_code={error_code} | found={result is not None}")
        return result

    def search_incidents(self, keyword: str) -> List[Dict]:
        """
        Search all incidents by keyword.
        Scans full table and filters client-side.
        Note: For large tables, add a GSI or use OpenSearch instead.
        """
        resp = self.incidents_tbl.scan()
        all_items = resp.get('Items', [])

        results = [
            item for item in all_items
            if keyword.lower() in item.get('description', '').lower()
            or keyword.lower() in item.get('error_code', '').lower()
        ]

        logger.info(
            f"[MEMORY] search_incidents | keyword={keyword} | found={len(results)}"
        )
        return results