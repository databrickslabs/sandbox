from __future__ import annotations

# --- Optional/lazy imports for external tools ---
try:
    from langchain_tavily import TavilySearch  # optional
except Exception:  # pragma: no cover
    TavilySearch = None  # type: ignore

try:
    from langchain_community.document_loaders import WebBaseLoader  # optional
except Exception:  # pragma: no cover
    WebBaseLoader = None  # type: ignore

import os
import aiohttp
import json
import asyncio
import logging
import ssl
import time
import hashlib
import re as _re
from typing import Dict, Any, Optional, List, Union, Tuple

import requests
import backoff
import pandas as pd

from databricks.sdk.core import Config

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("helper")


# -----------------------------------------------------------------------------
# Databricks OAuth config (single source of truth)
# -----------------------------------------------------------------------------
_CFG = Config()  # reads workspace & OAuth app from env/metadata
DATABRICKS_HOST: str = _CFG.hostname  # hostname (no protocol)

import os
from typing import List, Dict, Tuple
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

#os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")  # don't hardcode in code 
def tavily_topk_contents(question: str, k: int = 3) -> Tuple[List[Dict], str]:
    """
    Return (top-k results, combined content). If no API key or any error, returns ([], "").
    """
    if not os.getenv("TAVILY_API_KEY"):
        return [], ""  # no key -> no internet context

    tavily = TavilySearchAPIWrapper()
    try:
        print("Working with tavily, got the api key")
        results = tavily.results(query=question, max_results=k)
        # Normalize shapes
        if isinstance(results, dict) and "results" in results:
            results = results["results"]
        results = (results or [])[:k]

        combined = "\n\n".join(
            r.get("content", "").strip() for r in results if r.get("content")
        ).strip()
        return results, combined
    except Exception:
        # Network/quotas/shape issues -> fallback
        return [], ""


def _get_oauth_token() -> str:
    """Fetch a *fresh* OAuth token every time to avoid staleness."""
    try:
        return _CFG.oauth_token().access_token
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to mint OAuth token: %s", e)
        raise


def auth_headers() -> dict:
    """Return headers using a *fresh* OAuth token (ignore any legacy tokens)."""
    return {
        "Authorization": f"Bearer {_get_oauth_token()}",
        "Content-Type": "application/json",
    }


# -----------------------------------------------------------------------------
# Async Genie fetch (used by /fetch-schema etc.)
# -----------------------------------------------------------------------------
_ALLOW_INSECURE = os.getenv("ALLOW_INSECURE_SSL", "false").lower() in ("1", "true", "yes")


async def _raw_fetch_answer(
    workspace_url: str,
    genie_room_id: str,
    access_token: Optional[str],
    input_text: str,
    conversation_id: Optional[str] = None,
) -> dict:
    """Asynchronously fetch an answer from Databricks Genie.

    Note: `access_token` is ignored on purpose; we always use fresh OAuth.
    """
    if not workspace_url.endswith("/"):
        workspace_url += "/"

    headers = auth_headers()

    # Optional insecure SSL (for internal envs); secure by default.
    connector = None
    if _ALLOW_INSECURE:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)

    max_query_retries = 3
    query_retry_count = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            if conversation_id:
                logger.info("Continuing conversation: %s", conversation_id)
                continue_url = (
                    f"{workspace_url}api/2.0/genie/spaces/{genie_room_id}/conversations/{conversation_id}/messages"
                )
                payload_continue = {"content": input_text}
                async with session.post(continue_url, json=payload_continue, headers=headers) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error("Error continuing conversation: %s - %s", resp.status, txt)
                        return {"error": f"API error: {resp.status} - {txt}", "conversation_id": conversation_id}
                    response_json = await resp.json()
                if "message_id" not in response_json:
                    logger.error("Unexpected response (missing message_id): %s", response_json)
                    return {"error": "Unexpected response format from API", "conversation_id": conversation_id}
                message_id = response_json["message_id"]
            else:
                start_conv_url = f"{workspace_url}api/2.0/genie/spaces/{genie_room_id}/start-conversation"
                payload_start = {"content": input_text}
                async with session.post(start_conv_url, json=payload_start, headers=headers) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error("Error starting conversation: %s - %s", resp.status, txt)
                        return {"error": f"API error: {resp.status} - {txt}"}
                    response_json = await resp.json()

                if "message_id" not in response_json:
                    logger.error("Unexpected response (missing message_id): %s", response_json)
                    return {"error": "Unexpected response format from API"}
                message_id = response_json["message_id"]
                if "message" in response_json and "conversation_id" in response_json["message"]:
                    conversation_id = response_json["message"]["conversation_id"]
                elif "conversation_id" in response_json:
                    conversation_id = response_json["conversation_id"]
                else:
                    logger.error("Missing conversation_id in API response: %s", response_json)
                    return {"error": "Missing conversation_id in API response"}

            logger.info("Conversation ID: %s, Message ID: %s", conversation_id, message_id)

            while query_retry_count < max_query_retries:
                if query_retry_count:
                    logger.info("Retry attempt %d/%d", query_retry_count + 1, max_query_retries)
                poll_url = (
                    f"{workspace_url}api/2.0/genie/spaces/{genie_room_id}/conversations/"
                    f"{conversation_id}/messages/{message_id}"
                )
                max_polls = 300  # ~4-10 min depending on sleep
                retry_interval = 2

                for attempt in range(max_polls):
                    async with session.get(poll_url, headers=headers) as pres:
                        if pres.status != 200:
                            et = await pres.text()
                            logger.error("Polling error: %s - %s", pres.status, et)
                            await asyncio.sleep(retry_interval)
                            continue
                        poll_json = await pres.json()

                    if poll_json.get("attachments"):
                        attachment = poll_json["attachments"][0]
                        attachment_id = attachment.get("attachment_id")
                        
                        # Extract SQL query from the attachment if available
                        sql_query = None
                        if "query" in attachment:
                            query_info = attachment.get("query", {})
                            if isinstance(query_info, dict):
                                sql_query = query_info.get("query", "")
                            else:
                                sql_query = str(query_info)
                            logger.info(f"🔍 Extracted SQL query from attachment: {sql_query[:100] if sql_query else 'None'}...")
                        
                        answer_url = (
                            f"{workspace_url}api/2.0/genie/spaces/{genie_room_id}/conversations/"
                            f"{conversation_id}/messages/{message_id}/attachments/{attachment_id}/query-result"
                        )
                        async with session.get(answer_url, headers=headers) as r2:
                            if r2.status != 200:
                                et = await r2.text()
                                logger.error("Result fetch error: %s - %s", r2.status, et)
                                break
                            result_json = await r2.json()

                        state = result_json.get("statement_response", {}).get("status", {}).get("state")
                        if state == "SUCCEEDED":
                            logger.info("Query succeeded")
                            result_json["conversation_id"] = conversation_id
                            # Include the SQL query in the result
                            if sql_query and sql_query.strip():
                                result_json["sql_query"] = sql_query.strip()
                                logger.info(f"✅ Added SQL query to result: {sql_query[:100]}...")
                            return result_json
                        elif state == "FAILED":
                            logger.error("Query failed (attempt %d/%d)", query_retry_count + 1, max_query_retries)
                            if query_retry_count < max_query_retries - 1:
                                query_retry_count += 1
                                await asyncio.sleep(2)
                                break
                            else:
                                return {
                                    "error": "Query failed to execute after multiple attempts.",
                                    "conversation_id": conversation_id,
                                    "attempts": query_retry_count + 1,
                                }
                        # else keep polling

                    if attempt % 10 == 0:
                        logger.info("Polling attempt %d/%d", attempt + 1, max_polls)
                    await asyncio.sleep(retry_interval)

                if query_retry_count < max_query_retries - 1:
                    query_retry_count += 1
                else:
                    break

            logger.warning("Failed to get result after %d attempts", query_retry_count + 1)
            return {
                "error": f"Could not get query result after {query_retry_count + 1} attempts.",
                "conversation_id": conversation_id,
                "attempts": query_retry_count + 1,
            }

        except aiohttp.ClientError as e:
            logger.exception("HTTP error in fetch_answer: %s", e)
            return {"error": f"Network error: {str(e)}", "conversation_id": conversation_id}
        except Exception as e:
            logger.exception("Unexpected error in fetch_answer: %s", e)
            return {"error": f"Unexpected error: {str(e)}", "conversation_id": conversation_id}


# --------------------
# Lightweight TTL cache for fetch_answer
# --------------------
_ANSWER_CACHE_TTL = int(os.getenv("ANSWER_CACHE_TTL", "300"))  # seconds
_ANSWER_CACHE_MAX = int(os.getenv("ANSWER_CACHE_MAX", "512"))  # entries
_ANSWER_CACHE: Dict[str, Tuple[float, dict]] = {}
_ANSWER_CACHE_LOCK = asyncio.Lock()


def _normalize_q(q: str) -> str:
    try:
        q = q.strip()
        q = _re.sub(r"\s+", " ", q)
        return q[:4096]
    except Exception:
        return q


def _answer_cache_key(workspace_url: str, genie_room_id: str, input_text: str, conversation_id: Optional[str]):
    base = f"{workspace_url}|{genie_room_id}|{_normalize_q(input_text)}|{conversation_id or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def fetch_answer(workspace_url, genie_room_id, access_token, input_text, conversation_id=None):
    """Cached wrapper over _raw_fetch_answer. Set ANSWER_CACHE_TTL/ANSWER_CACHE_MAX via env."""
    key = _answer_cache_key(workspace_url, genie_room_id, input_text, conversation_id)
    now = time.time()
    # Try cache
    try:
        async with _ANSWER_CACHE_LOCK:
            entry = _ANSWER_CACHE.get(key)
            if entry and (now - entry[0]) < _ANSWER_CACHE_TTL:
                return entry[1]
    except Exception:
        pass

    data = await _raw_fetch_answer(workspace_url, genie_room_id, access_token, input_text, conversation_id)

    # Avoid caching obvious auth failures
    try:
        if isinstance(data, dict) and "error" in data and "Invalid Token" in str(data.get("error", "")):
            return data
    except Exception:
        pass

    # Extract SQL query from the response and add it to the data
    if isinstance(data, dict) and "error" not in data:
        sql_query = extract_sql_from_response(data)
        if sql_query:
            data["sql_query"] = sql_query

    # Store
    try:
        async with _ANSWER_CACHE_LOCK:
            if len(_ANSWER_CACHE) >= _ANSWER_CACHE_MAX:
                try:
                    oldest_key = next(iter(_ANSWER_CACHE))
                    _ANSWER_CACHE.pop(oldest_key, None)
                except Exception:
                    _ANSWER_CACHE.clear()
            _ANSWER_CACHE[key] = (time.time(), data)
    except Exception:
        pass

    return data



def extract_sql_from_response(response_data: dict) -> Optional[str]:
    """Extract SQL query from Genie API response data."""
    try:
        # Log the response structure for debugging
        logger.info(f"🔍 Debugging response structure: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
        
        # Check if response has statement_response with query
        statement_response = response_data.get("statement_response", {})
        if statement_response:
            logger.info(f"🔍 Found statement_response: {list(statement_response.keys())}")
            query = statement_response.get("query", "")
            if query and query.strip():
                logger.info(f"✅ Found SQL query in statement_response: {query[:100]}...")
                return query.strip()
        
        # Check if response has attachments with query information
        attachments = response_data.get("attachments", [])
        if attachments:
            logger.info(f"🔍 Found attachments: {len(attachments)} items")
            for i, attachment in enumerate(attachments):
                logger.info(f"🔍 Attachment {i}: {list(attachment.keys()) if isinstance(attachment, dict) else 'Not a dict'}")
                if "query" in attachment:
                    query_info = attachment.get("query", {})
                    logger.info(f"🔍 Found query in attachment: {list(query_info.keys()) if isinstance(query_info, dict) else query_info}")
                    if isinstance(query_info, dict):
                        query_text = query_info.get("query", "")
                    else:
                        query_text = str(query_info)
                    if query_text and query_text.strip():
                        logger.info(f"✅ Found SQL query in attachments: {query_text[:100]}...")
                        return query_text.strip()
        
        # Check for SQL in result_data if available
        result_data = response_data.get("result_data", {})
        if result_data:
            logger.info(f"🔍 Found result_data: {list(result_data.keys())}")
            if "query" in result_data:
                query_text = result_data.get("query", "")
                if query_text and query_text.strip():
                    logger.info(f"✅ Found SQL query in result_data: {query_text[:100]}...")
                    return query_text.strip()
        
        # Additional check for direct query field
        if "query" in response_data:
            query_text = response_data.get("query", "")
            if query_text and query_text.strip():
                logger.info(f"✅ Found SQL query in root: {query_text[:100]}...")
                return query_text.strip()
                
        logger.warning("⚠️ No SQL query found in response")
        return None
    except Exception as e:
        logger.warning(f"Error extracting SQL from response: {str(e)}")
        return None
