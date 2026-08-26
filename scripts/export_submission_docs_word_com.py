from pathlib import Path
import shutil
import win32com.client

root = Path(__file__).resolve().parents[1]
works = root / "作品"
stems = [
    "TraceGuard_最终报告",
    "TraceGuard_原创性声明_待签章",
    "TraceGuard_测试报告",
    "TraceGuard_作品简介",
]

word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    for stem in stems:
        source = works / f"{stem}.docx"
        target = works / f"{stem}.pdf"
        document = word.Documents.Open(str(source), ReadOnly=True, AddToRecentFiles=False)
        try:
            document.ExportAsFixedFormat(
                str(target), 17, False, 0, 0, 0, 0, 0, True, False, 0, True, True, False
            )
        finally:
            document.Close(False)
        print(target)
finally:
    word.Quit()

shutil.copy2(works / "TraceGuard_最终报告.pdf", works / "报告.pdf")
shutil.copy2(works / "TraceGuard_原创性声明_待签章.pdf", works / "原创性说明.pdf")
