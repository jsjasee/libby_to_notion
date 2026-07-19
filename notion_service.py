import os
import time

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Any

MAX_NOTION_RICH_TEXT = 2000
MAX_APPEND_CHILDREN = 100
APPEND_DELAY_SECONDS = 0.35
MAX_APPEND_RETRIES = 3
REFLECTION_PROMPTS = [
    "Why did I read this book?",
    "What is it about?",
    "What are some of the best ideas worth keeping?",
    "What will I do differently? (How can I apply this)",
    "Was it worth it? (Rating)",
]


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _build_notion_client() -> tuple[Client, str, str, str | None]:
    """Load Notion settings and return a ready client plus parent/tag/template IDs."""
    load_dotenv()
    token = _get_required_env("NOTION_TOKEN")
    data_source_id = _get_required_env("NOTION_NOTES_DATA_SOURCE_ID")
    tag_page_id = _get_required_env("NOTION_TAG_PAGE_ID")
    template_id = _get_optional_env("TEMPLATE_ID")
    return Client(auth=token), data_source_id, tag_page_id, template_id


def _build_page_request(book_title: str, tag_page_id: str, template_id: str | None) -> dict:
    request_body: dict[str, Any] = {
        "properties": {
            "Title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": book_title},
                    }
                ]
            },
            "Tag": {"relation": [{"id": tag_page_id}]},
        }
    }
    if template_id:
        request_body["template"] = {"type": "template_id", "template_id": template_id}
    return request_body


def _rich_text(content: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": content}}]


def _note_rich_text(content: str, include_label: bool) -> list[dict[str, Any]]:
    if not include_label:
        return _rich_text(content)
    return [
        {
            "type": "text",
            "text": {"content": "Note: "},
            "annotations": {"bold": True},
        },
        {"type": "text", "text": {"content": content}},
    ]


def _split_quote(quote: str) -> list[str]:
    text = quote.strip() # strips the whitespaces
    # the code below splits the quote into chunks of 2000 words in a list
    return [text[i : i + MAX_NOTION_RICH_TEXT] for i in range(0, len(text), MAX_NOTION_RICH_TEXT)] or [""]


def build_reflection_toggle_block() -> dict[str, Any]:
    """Build the top-level reflection toggle with its prompt bullets."""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": _rich_text("Reflection Template"),
            "children": [
                {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _rich_text(prompt)}}
                for prompt in REFLECTION_PROMPTS
            ],
        },
    }


def build_chapter_toggle_block(chapter: str) -> dict[str, Any]:
    """Build a chapter TOGGLE payload for one grouped chapter."""
    chapter_name = chapter.strip() or "(Blank chapter)"
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {"rich_text": _rich_text(chapter_name)},
    }


def _build_note_blocks(note: str) -> list[dict[str, Any]]:
    note_chunks = _split_quote(note)
    return [
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _note_rich_text(chunk, index == 0)},
        }
        for index, chunk in enumerate(note_chunks)
    ]


def build_quote_bullet_blocks(quotes: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build quote bullets, with optional note bullets nested under the last quote chunk."""
    blocks: list[dict[str, Any]] = []
    for item in quotes:
        quote = item["quote"]
        note = item["note"]
        chunks = _split_quote(quote)
        for index, chunk in enumerate(chunks):
            bullet = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich_text(chunk)},
            }
            if note and index == len(chunks) - 1:
                # attach the note to the last quote chunk (if the quotes need to be split into chunks)
                bullet["bulleted_list_item"]["children"] = _build_note_blocks(note)
            blocks.append(bullet)
    return blocks


def batch_append_children(children: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split block children into Notion append-sized batches."""
    # this is a similar concept to the _split_quote() function except now we are splitting it into 100 payloads (a fancy term for request body) at a time for processing.
    return [children[i : i + MAX_APPEND_CHILDREN] for i in range(0, len(children), MAX_APPEND_CHILDREN)]

def append_block_children(client: Client, parent_id: str, children: list[dict[str, Any]]) -> dict[
                                                                                                 str, bool | str | Any] | \
                                                                                             dict[
                                                                                                 str, bool | str | dict[
                                                                                                     Any, Any]]:
    """Append one child batch to Notion with pacing and capped retries.

    Args:
        client: Ready Notion client.
        parent_id: Page or block ID receiving these children.
        children: One append-sized batch of block payloads.

    Returns:
        A result dict with `ok` plus an error message when the append fails.
    """
    time.sleep(APPEND_DELAY_SECONDS)
    for attempt in range(MAX_APPEND_RETRIES + 1):
        try:
            response = client.blocks.children.append(block_id=parent_id, children=children)
            return {"ok": True, "error": "", "response": response}
        except APIResponseError as exc:
            status = getattr(exc, "status", None)
            retryable = status == 429 or (isinstance(status, int) and status >= 500)
            if not retryable or attempt == MAX_APPEND_RETRIES:
                return {"ok": False, "error": f"Failed to append blocks to {parent_id}: {exc}", "response": {}}
            time.sleep(APPEND_DELAY_SECONDS * (2 ** (attempt + 1))) # this is an exponential backoff - make it wait longer after each failed retry.

    return {"ok": False, "error": f"Failed to append blocks to {parent_id}. Please try again later.", "response": {}}


def _first_block_id(result: dict[str, Any]) -> str:
    children = result["response"].get("results", [])
    return children[0].get("id", "").strip() if children else ""


def append_template_toggle(client: Client, page_id: str) -> dict[str, Any]:
    """Append the reflection template toggle to a page."""
    return append_block_children(client, page_id, [build_reflection_toggle_block()])


def append_chapter_toggle(client: Client, page_id: str, chapter: str) -> dict[str, Any]:
    """Append one chapter toggle and return its created block ID."""
    result = append_block_children(client, page_id, [build_chapter_toggle_block(chapter)])
    block_id = _first_block_id(result) if result["ok"] else ""
    if result["ok"] and not block_id:
        return {"ok": False, "error": f"Notion did not return a block ID for chapter: {chapter or '(Blank chapter)'}", "block_id": ""}
    return {"ok": result["ok"], "error": result["error"], "block_id": block_id}


def append_quote_bullets(client: Client, toggle_block_id: str, quotes: list[dict[str, str]]) -> dict[str, str | bool]:
    """Append all quote bullets under one chapter toggle."""
    for batch in batch_append_children(build_quote_bullet_blocks(quotes)):
        result = append_block_children(client, toggle_block_id, batch)
        if not result["ok"]:
            return {"ok": False, "error": result["error"]}
    return {"ok": True, "error": ""}


def append_page_body(page_id: str, grouped_chapters: dict[str, list[dict[str, str]]]) -> dict[str, str | bool]:
    """Append the reflection toggle and all chapter quote blocks to a page."""
    client, _, _, _ = _build_notion_client()
    result = append_template_toggle(client, page_id)
    if not result["ok"]:
        return {"ok": False, "status": "incomplete", "error": result["error"]}

    for chapter, quotes in grouped_chapters.items():
        chapter_result = append_chapter_toggle(client, page_id, chapter)
        if not chapter_result["ok"]:
            return {"ok": False, "status": "incomplete", "error": chapter_result["error"]}
        quote_result = append_quote_bullets(client, chapter_result["block_id"], quotes)
        if not quote_result["ok"]:
            return {"ok": False, "status": "incomplete", "error": quote_result["error"]}

    return {"ok": True, "status": "complete", "error": ""}


def create_notes_page(book_title: str) -> dict:
    """Create a Notes page and return its Notion identifiers.

    Args:
        book_title: Title to write into the Notion `Title` property.

    Returns:
        A dict containing the created page ID and URL.

    Raises:
        ValueError: If the title or required environment variables are missing.
        RuntimeError: If Notion rejects the page creation request.
    """
    if not book_title.strip():
        raise ValueError("Book title is required.")

    client, data_source_id, tag_page_id, template_id = _build_notion_client()
    request_body = {
        "parent": {"data_source_id": data_source_id},
        **_build_page_request(book_title.strip(), tag_page_id, template_id),
    }

    try:
        response = client.pages.create(**request_body)
    except APIResponseError as exc:
        raise RuntimeError(f"Failed to create Notion page: {exc}") from exc

    page_id = response.get("id", "").strip()
    page_url = response.get("url", "").strip()
    if not page_id or not page_url:
        raise RuntimeError("Notion created the page but did not return both page ID and URL.")
    return {"page_id": page_id, "page_url": page_url}


def test_notion_connection() -> str:
    """Create a dummy Notes page and return its Notion URL.

    Returns:
        The created Notion page URL.

    Raises:
        ValueError: If a required environment variable is missing.
        RuntimeError: If Notion rejects the page creation request.
    """
    return create_notes_page("API Test - Libby Import")["page_url"]
