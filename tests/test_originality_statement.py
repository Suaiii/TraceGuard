"""Official originality statement builder tests."""

from pathlib import Path

import pytest
from docx import Document

from scripts.build_originality_statement import PROJECT_TITLE, build_statement


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "原创性说明.docx"


@pytest.mark.skipif(
    not TEMPLATE_PATH.is_file(),
    reason="official originality template is an external competition asset",
)
def test_build_statement_fills_only_project_title(tmp_path):
    output = tmp_path / "originality.docx"

    build_statement(TEMPLATE_PATH, output)

    document = Document(output)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert PROJECT_TITLE in text
    assert "作品参赛团队组员（签名）：" in text
    assert "年     月    日" in text
    assert len(document.sections) == 1
