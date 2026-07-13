"""Prepare the official originality statement without filling handwritten fields."""

from argparse import ArgumentParser
from pathlib import Path

from docx import Document


PROJECT_TITLE = "TraceGuard：面向跨域 AIGC 图像的可解释伪造检测与篡改取证平台"


def build_statement(template_path: Path, output_path: Path) -> None:
    document = Document(template_path)
    declaration = document.paragraphs[1]
    blank_run = next((run for run in declaration.runs if run.text.strip() == ""), None)
    if blank_run is None:
        raise ValueError("official statement title placeholder was not found")

    blank_run.text = PROJECT_TITLE
    document.core_properties.title = "TraceGuard 作品原创性声明"
    document.core_properties.author = "TraceGuard 参赛团队"
    document.core_properties.last_modified_by = "TraceGuard 参赛团队"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def main() -> None:
    parser = ArgumentParser(description="Prepare the official originality statement")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_statement(args.template, args.output)


if __name__ == "__main__":
    main()
