# Libby Highlights to Notion Importer

<aside>
🛠️

**PRD Revision Log — 2 Jul 2026 (post senior-engineer review). Changed items are marked 🔧 in each section:**

- **Tech Stack + Features 1, 5, 8:** the Notion parent env var is renamed to the **data source ID** (`NOTION_NOTES_DATA_SOURCE_ID`); the page parent is now a data source on Notion API version `2025-09-03`.
- **Feature 6 (Page Body Blocks):** added 2,000-character quote-splitting, rate-limit pacing + retry/back-off, and partial-failure resume with an "Incomplete" result.
- **Feature 7 (Gradio App):** the "Create Notion Page" button now disables while running (duplicate-import guard) and reports an "Incomplete" status + error on partial failure.
- **Assumptions / Open Questions + Features 7, 8:** data-source decision recorded; duplicate-chapter question resolved (merge); deployed-app auth resolved — **public Space + Gradio password gate**.
</aside>

## What it is

A personal web app that imports one Libby highlights CSV into the user's Notion Notes database. It creates a new Notion page with a reflection toggle, chapter toggles, and quote bullet points.

## Success Criteria

- [ ]  A local script can create a dummy page in the Notion Notes database with the correct `Title` and `Tag` relation.
- [ ]  The app accepts exactly one Libby CSV file and rejects missing `chapter` or `quote` columns with a clear error.
- [ ]  The preview shows the total rows, total chapters, total quotes, and the first few chapter names with quote counts.
- [ ]  Clicking "Create Notion Page" creates one new Notion page with naturally ordered chapter toggles and quote bullets.
- [ ]  A full Libby CSV imports successfully without hitting Notion block request limits. ( We will try it with a csv file with 322 rows first)

## Tech Stack & Constraints

- Language / Runtime: Python, uv (but we will need a requirements.txt later on since that is required for huggingface deployment)
- Framework / Libraries: Gradio, pandas, official Notion Python client, python-dotenv
- Storage / Data: Local `.env` file for secrets; no persistent storage for uploaded CSV files
- Deployment: Hugging Face Spaces using Gradio SDK, **public Space but Gradio password-gated** (`auth=(APP_USERNAME, APP_PASSWORD)`)
- Constraints: One user only, one Libby CSV upload only, Libby CSV format only, Notion Notes database only, hardcoded Tag relation from `.env`, buildable within one week

## Features & TODOs

### Feature 1 — Notion Environment Setup

Priority: P0
Description: Set up the local Notion connection so the app can create pages inside the Notes database. This matters because Notion permissions should be tested before CSV parsing is added.
Acceptance Criteria:

- Running the dummy script creates a page titled `API Test - Libby Import` in the Notes database.
- The created dummy page has the hardcoded Tag relation attached.
- The script returns the Notion page URL or a clear error message.

TODOs:

- [ ]  Create `.env.example` with `NOTION_TOKEN`, `NOTION_NOTES_DATA_SOURCE_ID`, and `NOTION_TAG_PAGE_ID`.
- [ ]  Install `notion-client`, `python-dotenv`, `pandas`, and `gradio` in the project environment.
- [ ]  Create `notion_service.py` and load the three required environment variables using `python-dotenv`.
- [ ]  Create `test_notion_connection()` that creates a dummy page titled `API Test - Libby Import`.
- [ ]  Add the `Title` property using the book title text format expected by Notion.
- [ ]  Add the `Tag` relation using `NOTION_TAG_PAGE_ID`.
- [ ]  Print or return the created Notion page URL after the dummy page is created.
- [ ]  Manually confirm the dummy page appears in the Notion Notes database.

### Feature 2 — Basic Project Structure

Priority: P0
Description: Create a simple beginner-friendly code structure so CSV parsing, Notion logic, and Gradio UI are separated.
Acceptance Criteria:

- The project can be run locally with one clear command.
- Each major responsibility has its own file.
- Secrets are not committed to Git.

TODOs:

- [ ]  Create `app.py` for the Gradio interface.
- [ ]  Create `csv_parser.py` for Libby CSV parsing logic.
- [ ]  Create `notion_service.py` for Notion page and block creation logic.
- [ ]  Create `.gitignore` that excludes `.env`, uploaded CSV files, Python cache folders, and virtual environment folders.
- [ ]  Create `README.md` with local setup steps and the command to run the Gradio app.

### Feature 3 — Libby CSV Parser

Priority: P0
Description: Read the Libby CSV and convert it into grouped chapter data for Notion. The CSV is expected to contain `timestamp`, `chapter`, `percent`, `color`, and `quote`, but MVP only uses `chapter` and `quote`.
Acceptance Criteria:

- A valid Libby CSV returns grouped quotes by chapter.
- Missing `chapter` or `quote` columns returns a clear error.
- Blank quotes are removed silently.
- The CSV order is flipped so the earliest highlight appears first.
- Chapters are grouped in the order they appear after flipping the CSV.

TODOs:

- [ ]  Create `parse_libby_csv(csv_path: str) -> dict` that reads the CSV using pandas.
- [ ]  Check that the CSV includes both `chapter` and `quote` columns.
- [ ]  Return a clear error message if `chapter` or `quote` is missing.
- [ ]  Reverse the dataframe row order so the bottom CSV row becomes the first processed row.
- [ ]  Strip whitespace from `chapter` and `quote` values.
- [ ]  Remove rows where `quote` is blank after whitespace cleaning.
- [ ]  Group quotes by chapter while preserving the flipped reading order.
- [ ]  Return a dictionary containing total rows, total chapters, total quotes, and grouped chapter data.

### Feature 4 — Import Preview

Priority: P0
Description: Show the user what will be imported before creating the Notion page. This reduces the chance of sending the wrong CSV or wrong book title into Notion.
Acceptance Criteria:

- Preview requires one uploaded CSV file.
- Preview shows total rows, total chapters, and total quotes.
- Preview shows the first few chapter names with quote counts.
- Preview does not show timestamp, percent, or color metadata.

TODOs:

- [ ]  Create `preview_import(csv_path: str) -> str`.
- [ ]  Call `parse_libby_csv()` inside `preview_import()`.
- [ ]  Format the preview text with total rows, total chapters, and total quotes.
- [ ]  Add the first 3 to 5 chapter names with their quote counts.
- [ ]  Return the parser error message if the CSV is invalid.

### Feature 5 — Notion Page Creation

Priority: P0
Description: Create the real Notion page inside the Notes database using the entered book title and hardcoded Tag relation.
Acceptance Criteria:

- Clicking "Create Notion Page" creates exactly one new page in the Notes database.
- The page title matches the Gradio book title field.
- The page has the hardcoded Tag relation attached.
- The function returns the created Notion page URL.

TODOs:

- [ ]  Create `create_notes_page(book_title: str) -> dict`.
- [ ]  Validate that `book_title` is not empty before calling Notion.
- [ ]  🔧 Create the Notion page using `NOTION_NOTES_DATA_SOURCE_ID` as the parent **data source** (Notion API version `2025-09-03`).
- [ ]  Set the `Title` property from the book title.
- [ ]  Set the `Tag` relation from `NOTION_TAG_PAGE_ID`.
- [ ]  Return the new page ID and page URL.
- [ ]  Show a clear error if Notion rejects the page creation request.

### Feature 6 — Notion Page Body Blocks

Priority: P0
Description: Add the actual page content after the page is created. The body should contain one reflection toggle, then one toggle per chapter, with quote bullets nested inside each chapter toggle.
Acceptance Criteria:

- The page contains a top-level `Reflection Template` toggle.
- Each chapter becomes one Notion toggle block.
- Each quote becomes a bullet point inside the correct chapter toggle.
- Quotes are added in batches so the app does not exceed Notion block request limits.
- The 322-row CSV imports without a block limit failure.
- 🔧 Any quote longer than 2,000 characters is split into consecutive bullet points of ≤ 2,000 characters each, preserving order (Notion rich-text hard limit).
- 🔧 Requests are paced with a short delay to stay under ~3 requests/second; a failed/429 request waits and retries before the import is considered failed.
- 🔧 Quotes sharing the same chapter name are merged into a single chapter toggle.

TODOs:

- [ ]  Create `append_template_toggle(page_id: str) -> None`.
- [ ]  Add reflection prompts inside the template toggle: `Why did I read this book?`, `What is it about?`, `What are some of the best ideas worth keeping?`, `What will I do differently? (How can I apply this)`, and `Was it worth it? (Rating)`.
- [ ]  Create `append_chapter_toggle(page_id: str, chapter: str) -> str` that creates one chapter toggle and returns its block ID.
- [ ]  Create `append_quote_bullets(toggle_block_id: str, quotes: list[str]) -> None`.
- [ ]  Split quote bullets into batches of fewer than 100 children per Notion append request.
- [ ]  Create `append_all_chapters(page_id: str, grouped_chapters: dict) -> None`.
- [ ]  Append chapters in the grouped order produced by the flipped CSV.
- [ ]  Show a clear error if a Notion block append request fails.
- [ ]  🔧 In `append_quote_bullets()`, split any quote > 2,000 characters into consecutive ≤ 2,000-character bullets (Notion `rich_text.text.content` hard limit).
- [ ]  🔧 Add a short delay between Notion requests (e.g. ~0.35s) to stay under the ~3 requests/second average rate limit.
- [ ]  🔧 On a failed or `429` request, wait a few seconds and retry with backoff (capped retries); on success, resume the remaining requests instead of aborting the whole import.
- [ ]  🔧 Group quotes by chapter name so repeated chapter names merge into one toggle.

### Feature 7 — Gradio Web App

Priority: P0
Description: Provide a simple UI to upload one CSV, enter the book title, preview the import, and create the Notion page.
Acceptance Criteria:

- The UI accepts only one CSV file.
- The user can enter the book title in a textbox.
- The user clicks `Preview` before creating the Notion page.
- The user clicks `Create Notion Page` and receives a Notion page URL.
- Uploaded CSV files are deleted after processing.
- 🔧 The `Create Notion Page` button is disabled while an import is running and re-enabled when it finishes, so it cannot be clicked twice.
- 🔧 If the import only partially succeeds after retries, the app still returns the Notion page link, marks the result **Incomplete**, and shows the error message so the user knows what to fix.

TODOs:

- [ ]  Create a Gradio file input that accepts one `.csv` file only.
- [ ]  Create a Gradio textbox for the book title.
- [ ]  Create a `Preview` button wired to `preview_import()`.
- [ ]  Create a `Create Notion Page` button wired to `run_import()`.
- [ ]  Create `run_import(csv_path: str, book_title: str) -> str`.
- [ ]  In `run_import()`, parse the CSV, create the Notion page, append the reflection toggle, append chapter toggles, and return the Notion page URL.
- [ ]  Delete the uploaded CSV file after `run_import()` finishes.
- [ ]  Show a clear error if the user tries to create a page without a CSV or book title.
- [ ]  🔧 Disable the `Create Notion Page` button on click and re-enable it once `run_import()` returns (prevents duplicate pages).
- [ ]  🔧 In `run_import()`, if some requests still fail after retries, return the page URL + an "Incomplete import" status + the error detail instead of raising.
- [ ]  🔧 Password-gate the app with `demo.launch(auth=(APP_USERNAME, APP_PASSWORD))`, reading the credentials from Space secrets.

### Feature 8 — Hugging Face Spaces Deployment

Priority: P0
Description: Deploy the Gradio app to Hugging Face Spaces so it can be used from the browser without running Python locally.
Acceptance Criteria:

- The app runs successfully on Hugging Face Spaces.
- Secrets are configured through Hugging Face Space secrets, not committed files.
- The Space does not store uploaded CSV files after processing.
- A real Libby CSV can be imported from the hosted app.

TODOs:

- [ ]  Create a Hugging Face Space using the Gradio SDK.
- [ ]  🔧 Add `NOTION_TOKEN`, `NOTION_NOTES_DATA_SOURCE_ID`, `NOTION_TAG_PAGE_ID`, `APP_USERNAME`, and `APP_PASSWORD` as Space secrets.
- [ ]  Push `app.py`, `csv_parser.py`, `notion_service.py`, `requirements.txt`, and `README.md` to the Space repo.
- [ ]  🔧 Set the Space visibility to public (the Gradio app itself is password-gated, so it stays locked).
- [ ]  Run the hosted app and confirm the UI loads.
- [ ]  Upload the real Libby CSV and confirm the preview works.
- [ ]  Create a real Notion page from the hosted app.
- [ ]  Confirm no uploaded CSV file remains after the import finishes.

### Feature 9 — Optional Notion Connection Test Button

Priority: P1
Description: Add a non-core button in the app that creates a dummy Notion page from the UI. This is useful for debugging Notion permissions without running a separate script.
Acceptance Criteria:

- Clicking the button creates a dummy test page.
- The button returns the dummy page URL or a clear error.
- The button is visually separate from the real import flow.

TODOs:

- [ ]  Add a `Test Notion Connection` button in Gradio below the main import controls.
- [ ]  Wire the button to `test_notion_connection()`.
- [ ]  Return the dummy page URL in the Gradio output area.
- [ ]  Add helper text telling the user that test pages must be deleted manually in Notion.

## Assumptions / Open Questions

- Assumption: The project name is intentionally written as `Libby Highlights to Notion Polarizing`.
- 🔧 Decision (2 Jul 2026): The app uses the **data source ID** (`NOTION_NOTES_DATA_SOURCE_ID`) as the page parent on Notion API version `2025-09-03` — not the legacy database ID.
- Assumption: The user will manually delete dummy Notion test pages.
- Assumption: The Notion Notes database has a title property named `Title`.
- Assumption: The Notion Notes database has a relation property named `Tag`.
- Assumption: The hardcoded tag page ID in `.env` points to the correct related Tag page.
- Assumption: The Notion integration has access to both the Notes database and the related Tags database/page source.
- Assumption: The Libby CSV format is fixed and includes at least `chapter` and `quote`.
- Assumption: The CSV export is newest-first, so the dataframe must be reversed before grouping.
- Assumption: Chapter order should follow the reversed CSV reading order, not a custom parser that extracts chapter numbers.
- Assumption: Blank quotes should be removed silently.
- Assumption: `timestamp`, `percent`, and `color` are out of scope for MVP imports.
- Assumption: Telegram UI, multiple CSV uploads, Notion templates, Notion buttons, multi-user accounts, persistent storage, and metadata-rich quote formatting are out of scope for MVP.
- 🔧 Resolved (2 Jul 2026): Repeated/duplicate chapter names are **merged** into a single toggle — quotes are grouped by chapter name regardless of their position in the file.
- 🔧 Resolved (2 Jul 2026): The Space will be **public** but the Gradio app is **password-gated** via `demo.launch(auth=(APP_USERNAME, APP_PASSWORD))`. Credentials are stored as Space secrets, so the app stays locked even though the Space is publicly reachable.