import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
import csv_parser
import notion_service

load_dotenv()

def preview_import(csv_path: str | None, _: str) -> str:
    """Build a short import preview from a single Libby CSV file.

    Args:
        csv_path: Uploaded CSV file path from Gradio.
        _: Unused book title input kept for the current Gradio callback shape.

    Returns:
        Preview text with totals and the first few chapter quote counts, or a parser error.
    """
    try:
        result = csv_parser.parse_libby_csv(csv_path)
    except ValueError as exc:
        return str(exc)

    grouped_chapters = result["grouped_chapters"]
    chapter_preview = list(grouped_chapters.items())[:5]
    lines = [
        f"Total rows: {result['total_rows']}",
        f"Total chapters: {result['total_chapters']}",
        f"Total quotes: {result['total_quotes']}",
        "",
        "Chapter preview:",
    ]

    if not chapter_preview:
        lines.append("- No quotes found.")
    else:
        for chapter, quotes in chapter_preview:
            chapter_name = chapter or "(Blank chapter)"
            lines.append(f"- {chapter_name}: {len(quotes)} quotes")

    return "\n".join(lines)


def _markdown_link(url: str) -> str:
    return f"[{url}]({url})"


def run_import(csv_file: str | None, book_title: str) -> tuple[str, str]:
    """Run the full Libby-to-Notion import and return status text plus a page link.

    Args:
        csv_file: Uploaded CSV file path from Gradio.
        book_title: Page title to create in Notion.

    Returns:
        A tuple of status text and optional markdown link output.
    """
    csv_path = Path(csv_file) if csv_file else None
    try:
        if not csv_file:
            return "Please upload a Libby CSV file.", ""
        if not book_title.strip():
            return "Please enter a book title.", ""

        parsed_csv = csv_parser.parse_libby_csv(csv_file)
        page = notion_service.create_notes_page(book_title)
        body_result = notion_service.append_page_body(
            page["page_id"],
            parsed_csv["grouped_chapters"],
        )

        if body_result["status"] == "incomplete":
            return (
                "Status: Incomplete import\n"
                f"Error: {body_result['error']}",
                _markdown_link(page["page_url"]),
            )

        return "Status: Complete", _markdown_link(page["page_url"]) # this second output is for the markdown link later on.
    except (ValueError, RuntimeError) as exc:
        return str(exc), ""
    finally:
        if csv_path and csv_path.exists():
            csv_path.unlink() # deletes the file


def _disable_import_button() -> gr.Button:
    # we have to disable the button when the user clicks on 'create notion page' to prevent duplicate notion pages from being created.
    return gr.Button(interactive=False)


def _enable_import_button() -> gr.Button:
    return gr.Button(interactive=True)


def _get_app_auth() -> tuple[str, str]:
    """Load the Gradio basic-auth credentials from environment variables."""
    username = os.getenv("APP_USERNAME", "").strip()
    password = os.getenv("APP_PASSWORD", "").strip()
    if not username or not password:
        raise ValueError("Missing APP_USERNAME or APP_PASSWORD.")
    return username, password


def build_app() -> gr.Blocks:
    """Build the Gradio app shell for the Libby import flow.

    Returns:
        The configured Gradio interface.
    """
    with gr.Blocks(title="Libby to Notion") as demo:
        gr.Markdown("# Libby to Notion")
        csv_file = gr.File(label="Libby CSV", file_types=[".csv"], type="filepath")
        book_title = gr.Textbox(label="Book Title")
        preview_output = gr.Textbox(label="Preview", lines=8, interactive=False)
        import_output = gr.Textbox(label="Import Result", lines=4, interactive=False)
        import_link = gr.Markdown()
        # We have a textbox (input_output) and markdown component (import_link), so that we can see the textbox loading when it is processing, and click on the link in the markdown later on

        gr.Button("Preview").click(
            fn=preview_import,
            inputs=[csv_file, book_title],
            outputs=preview_output,
        )

        create_button = gr.Button("Create Notion Page")
        # also note: the .then() here is event chaining in gradio, not exactly like the .then() in javascript promises
        create_button.click(
            fn=_disable_import_button,
            outputs=create_button, # we take the value returned by the function _disable_import_button and UPDATE create_button's button, instead of creating a new unrelated button
        ).then(
            fn=run_import,
            inputs=[csv_file, book_title],
            outputs=[import_output, import_link],
        ).then(
            fn=_enable_import_button,
            outputs=create_button,
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch(auth=_get_app_auth())
