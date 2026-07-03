import gradio as gr
import csv_parser
import notion_service


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


def run_import(csv_file: str | None, book_title: str) -> str:
    if not book_title:
        return "No book title provided."
    result = notion_service.create_notes_page(book_title)
    # print(result)
    return "Import is not implemented yet."

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

        gr.Button("Preview").click(
            fn=preview_import,
            inputs=[csv_file, book_title],
            outputs=preview_output,
        )
        gr.Button("Create Notion Page").click(
            fn=run_import,
            inputs=[csv_file, book_title],
            outputs=import_output,
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch()
