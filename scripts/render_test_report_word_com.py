from pathlib import Path
import win32com.client

root = Path(__file__).resolve().parents[1]
docx = root / "作品" / "TraceGuard_测试报告.docx"
pdf = root / "作品" / "TraceGuard_测试报告.pdf"
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
doc = word.Documents.Open(str(docx), ReadOnly=True, AddToRecentFiles=False)
try:
    doc.ExportAsFixedFormat(str(pdf), 17, False, 0, 0, 0, 0, 0, True, False, 0, True, True, False)
finally:
    doc.Close(False)
    word.Quit()
print(pdf)
