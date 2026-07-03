import os

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError


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


def test_notion_connection() -> str:
    """Create a dummy Notes page and return its Notion URL.

    Returns:
        The created Notion page URL.

    Raises:
        ValueError: If a required environment variable is missing.
        RuntimeError: If Notion rejects the page creation request.
    """
    client, data_source_id, tag_page_id, template_id = _build_notion_client()
    request_body = {
        "parent": {"data_source_id": data_source_id},
        "properties": {
            "Title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "API Test - Libby Import"},
                    }
                ]
            },
            "Tag": {"relation": [{"id": tag_page_id}]},
        },
    }
    if template_id:
        request_body["template"] = {"type": "template_id", "template_id": template_id}

    try:
        response = client.pages.create(**request_body)
    except APIResponseError as exc:
        raise RuntimeError(f"Failed to create Notion test page: {exc}") from exc

    page_url = response.get("url", "").strip()
    if not page_url:
        raise RuntimeError("Notion created the test page but did not return a page URL.")
    return page_url
