import os

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Any

MAX_NOTION_RICH_TEXT = 2000
MAX_APPEND_CHILDREN = 100
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


def build_quote_bullet_blocks(quotes: list[str]) -> list[dict[str, Any]]:
    """Build bullet blocks for quotes, splitting any quote over 2,000 characters."""
    blocks: list[dict[str, Any]] = []
    for quote in quotes:
        for chunk in _split_quote(quote):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": _rich_text(chunk)},
                }
            )
    return blocks


def batch_append_children(children: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split block children into Notion append-sized batches."""
    # this is a similar concept to the _split_quote() function except now we are splitting it into 100 payloads (a fancy term for request body) at a time for processing.
    return [children[i : i + MAX_APPEND_CHILDREN] for i in range(0, len(children), MAX_APPEND_CHILDREN)]

# ok so the flow is:
# 1. we create the chapter the toggle block first, the get the ID of that block from notion
# 2. we THEN create a bunch of quotes blocks (the list) - which will later be stuffed under that toggle block in step 1.
# 3. we pass the quote blocks in batch_append_children, however we must do it in batches of 100 otherwise it will overwhelm the api and cause error.
# Visualisation:
    # quotes (we have 205 quotes in here)
    # -> build_quote_bullet_blocks(quotes)
    # -> [bullet1, bullet2, bullet3, ... bullet205]
    # -> batch_append_children(...)
    # -> [
    #      [bullet1 ... bullet100], # this is batch 1, 100 quotes
    #      [bullet101 ... bullet200], # this is batch 2
    #      [bullet201 ... bullet205] # batch 3
    #    ]
    # -> append batch 1 under chapter toggle
    # -> append batch 2 under chapter toggle
    # -> append batch 3 under chapter toggle

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
