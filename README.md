# AI Script Analyzer

Tooling to catalogue Finacle customization scripts, categorize their integration style, and
automatically describe inputs, outputs, error messages, and functional test cases. The
solution now mirrors the desired architecture of **(1) ingestion**, **(2) embedding storage**,
**(3) two-step LLM reasoning**, and **(4) bulk Excel export** while keeping AI API calls optional
through caching and rich heuristics inspired by the sample analyzer.

## Architecture & Features

1. **Script Ingestion Pipeline** – `ScriptIngestionPipeline` normalizes Finacle bodies (using
   the `<--START ... END-->` markers from the provided Streamlit sample), splits them into
   configurable line-based chunks, and enriches each document with structured hints such as
   CALLSCRIPT targets, user hooks, detected inputs/outputs, and representative assignments.
2. **Embedding Store (Vector DB)** – `EmbeddingStore` keeps lightweight cosine-similarity
   vectors for every chunk so related logic across scripts can be retrieved without external
   dependencies.
3. **Two-Step LLM Workflow** – `HybridSummarizer` first generates a heuristic JSON summary
   (business summary, IOs, errors, and detailed functional test cases) and, if allowed,
   upgrades it with an LLM call that receives the most relevant chunks plus the auto-built
   hints. This keeps API usage low while still supporting the structured output contract.
4. **Bulk Excel Generation** – `export_analysis_to_excel` writes the consolidated workbook in
   pure Python so QA and business teams can filter, pivot, and annotate the dataset offline.

Additional highlights:

- Recursively scans directories for Finacle customization scripts (`.txt`, `.sql`, `.scr`, `.fnc` by default).
- Embedding-driven retrieval ensures cross-script scenarios appear in summaries/test cases.
- Builds a dependency graph between scripts to distinguish standalone vs. add-on components.
- Generates structured JSON test cases (id, name, preconditions, inputs, outcomes, errors) and
  stores them in the Excel workbook for easy handoff.
- Optional LLM hook with caching keeps API costs predictable; set `--max-api-calls 0` to stay
  100% heuristic.

## Getting Started

1. **Run the analyzer**

   ```bash
   python -m ai_script_analyzer.cli /path/to/finacle/scripts --output finacle_analysis.xlsx
   ```

   Useful flags:

   - `--extensions .sql .fnc .prc` – override the file extensions to scan.
   - `--summary-cache cache.json` – store and reuse structured JSON summaries to avoid repeated API hits.
   - `--max-api-calls 5` – cap the number of LLM requests (0 disables LLM usage entirely).
   - `--chunk-lines 120` – adjust chunk size used by the ingestion pipeline and embedding store.
   - `--similarity-top-k 8` – control how many related chunks feed each LLM prompt.

## Extending the Tool

- If you prefer to use a third-party Excel library (such as `openpyxl` or `pandas`),
  add it to `requirements.txt` and swap out the minimalist writer in
  `ai_script_analyzer/excel_exporter.py`.

- Update `AnalyzerConfig.script_extensions` or pass `--extensions` to match your repository.
- Customize the regex patterns inside `ai_script_analyzer/analyzer.py` if your scripts use
  different keywords for inputs, outputs, or errors.
- Plug in your own LLM callable via `HybridSummarizer` (for example, wrap Gemini per the sample
  Streamlit analyzer) and configure a cache file so that repeated runs rehydrate previous
  structured JSON summaries.
- Use the generated Excel workbook as the source of truth for business and QA teams when
  planning regression test coverage.
