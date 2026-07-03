import gradio as gr
import csv_parser
import notion_service


def preview_import(_: str | None, __: str) -> str:
    result = csv_parser.parse_libby_csv("libbyjourney-10217046-stop-people-pleasing---highlights.csv")
    # print(result)
    return "Preview is not implemented yet."


def run_import(_: str | None, __: str) -> str:
    result = notion_service.test_notion_connection()
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
