# Zotero PDF compatibility diagnosis and candidate validation

## Result

The original `zotero_read_pdf_pages` calls for `5WC9FHTZ` and `7KCJR9EB`, both `start_page=1`, `end_page=1`, `format="text"`, were reproduced with `isError=true` and `PDF parsing error: couldn't parse input: invalid file trailer`.

The installed `zotero-mcp-server 0.13.2` uses `pdf-inspector 0.2.6` for page counting and text extraction. Directly reading both real local file paths and their original bytes with that parser reproduces the error. PyMuPDF 1.26.7 opens both originals without its repair flag, extracts their requested first-page text, and renders their first pages. The failure is therefore a compatibility failure of the installed parsing path against these real PDF inputs; an API transport-corruption hypothesis is unnecessary to reproduce it.

Both PDFs have 137 bytes of `WebFastLoad`/`FileProperty` data after their last `%%EOF`. Removing this suffix only in memory did **not** fix `pdf-inspector`, so the suffix is not an established sole cause. No original PDF bytes were changed.

| Requested parent key | Resolved attachment | PDF pages | Requested PDF page | Printed page visible in rendering |
| --- | --- | ---: | ---: | --- |
| `5WC9FHTZ` | `E9UPS2W9` | 4 | 1 | 051 |
| `7KCJR9EB` | `PIHCARAE` | 6 | 1 | 94 |

The requested numbers are physical PDF page numbers, not the printed journal page labels.

## Installed-source evidence

All paths below are under `/Users/wangyuelin/.local/share/uv/tools/zotero-mcp-server/lib/python3.11/site-packages/`.

- `zotero_mcp/tools/read_pdf.py:90-125`: existing item/attachment resolver and preferred local-storage path.
- `zotero_mcp/tools/read_pdf.py:270-277`: shared text/image page-range validation calls `pdf_page_count`; this is where the original calls fail before page extraction.
- `zotero_mcp/extract.py:117-128`: `pdf_page_count` delegates to `pdf_inspector.classify_pdf`.
- `zotero_mcp/tools/read_pdf.py:327-328`: original 1-based requested range becomes absolute 0-based extraction indices.
- `zotero_mcp/tools/read_pdf.py:457-475`: image mode also uses the same page-count validation, then the existing PyMuPDF renderer, rectangle handling, and image limits. Merely changing the original call to `format="image"` does not bypass the failing count.

## Candidate process-local wrapper

Candidate: `zotero_compat.py` in this directory. It uses the existing installed environment and ordinary `zotero_mcp.cli.main()` entry point. It does not write package files, PDFs, credentials, or configuration.

The wrapper changes only the `zotero_mcp.tools.read_pdf` module's in-process bindings:

1. `pdf_page_count`: try the original parser, then PyMuPDF only for a recognized parser failure.
2. `extract_pdf`: preserve original success; on a recognized parser failure, build the original `ExtractedDoc` type from selected PyMuPDF pages, retaining absolute 0-based page indices.
3. `read_pdf_text` and `render_pdf_pages`: add an explicit PyMuPDF compatibility annotation only when the call used a fallback. Existing tool formatting, requested item/attachment key, 1-based labels, range validation, limits, image rendering, and crop validation continue through the original functions.

The global `zotero_mcp.extract` module is not patched. Existing Codex launches that do not invoke this wrapper retain their existing behavior. Non-parser failures and failures of the fallback propagate as errors. Tested package versions are pinned; a version mismatch fails startup explicitly with exit code 78 and requires review before using a new version.

Text fallback is plain extracted text and does not reconstruct the original Markdown layout. Pages without extractable text are marked for OCR by the original tool response; the wrapper does not run OCR. Use the returned page images when page layout, figures, tables, or text-layer completeness matters.

## Validation

- Seven regression tests pass (`test_zotero_compat.py`). They cover real source first-page text and images, byte-identical successful original text/image responses on a healthy PDF, non-parser errors, fallback errors, page/crop errors, and explicit version mismatch.
- A fresh candidate-wrapper stdio MCP subprocess was exercised using the existing MCP client, original live attachment resolution, and `ZOTERO_LOCAL=true`: both requested parent keys returned first-page text with the engine annotation; `5WC9FHTZ` also returned one first-page PNG. All three calls had `is_error=false`. No search/connection acceptance was repeated.
- `mcp-wrapper-verification.json` records those three MCP calls and the parent-to-attachment mapping. `wrapper-source-verification.json` records additional direct checks against both real source PDFs.
- First-page images were visually inspected: titles match the two source records, and the physical first pages show printed pages 051 and 94 respectively.
- SHA-256 before and after is unchanged for both originals:
  - `5WC9FHTZ` / `E9UPS2W9`: `14db38cfc741c5da5b821dcd652b2bb04971318bfb41f3a156ff7827d064764c`
  - `7KCJR9EB` / `PIHCARAE`: `6b30cf06b88ef879e5e181d79d5933539afc6f086be7e44b63940b602a25b6e4`

This agent made only diagnosis/candidate files in the assigned temporary directory. Deployment and Linux profile retesting belong to the primary agent.

## Reproduce candidate checks

```sh
/Users/wangyuelin/.local/share/uv/tools/zotero-mcp-server/bin/python -B -m unittest discover -s /private/tmp/zotero-academic-diagnosis -p 'test_zotero_compat.py' -v
/Users/wangyuelin/.local/share/uv/tools/zotero-mcp-server/bin/python -B /private/tmp/zotero-academic-diagnosis/verify_mcp_wrapper.py
```
