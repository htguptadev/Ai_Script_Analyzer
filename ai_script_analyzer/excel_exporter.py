"""Pure-Python Excel writer tailored for the analyzer output."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from .models import ScriptAnalysisResult

HEADER = [
    "Script Name",
    "Path",
    "Category",
    "Business Summary",
    "Inputs",
    "Outputs",
    "Error Conditions",
    "Dependencies",
    "Dependents",
    "Functional Test Cases",
]


def export_analysis_to_excel(result: ScriptAnalysisResult, output_path: Path) -> None:
    rows = [HEADER] + [script.as_row() for script in result.scripts]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        _write_static_parts(archive)
        _write_sheet(archive, rows)


def _write_static_parts(archive: ZipFile) -> None:
    archive.writestr(
        "[Content_Types].xml",
        """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
""",
    )
    archive.writestr(
        "_rels/.rels",
        """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
    )
    archive.writestr(
        "xl/workbook.xml",
        """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Analysis" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""",
    )
    archive.writestr(
        "xl/_rels/workbook.xml.rels",
        """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
""",
    )
    archive.writestr(
        "xl/styles.xml",
        """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>
""",
    )


def _write_sheet(archive: ZipFile, rows: List[List[str]]) -> None:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_letter(col_index)}{row_index}"
            safe_value = escape(value or "")
            cells.append(f"<c r=\"{cell_ref}\" t=\"str\"><v>{safe_value}</v></c>")
        sheet_rows.append(f"<row r=\"{row_index}\">{''.join(cells)}</row>")
    sheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData>"
        + "</worksheet>"
    )
    archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
