import pypdf
import sys

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"C:\Users\Admin\AppData\Local\DobotLab\resources\helpDoc\HelpDoc-MagicianGo-en.pdf"
reader = pypdf.PdfReader(pdf_path)

print(f"Total pages: {len(reader.pages)}")

search_terms = ["trace", "running_mode", "runningMode", "line following", "follow"]

for i, page in enumerate(reader.pages):
    text = page.extract_text()
    for term in search_terms:
        if term.lower() in text.lower():
            print(f"--- Page {i+1} matches '{term}': ---")
            lines = text.split("\n")
            for line in lines:
                if term.lower() in line.lower():
                    print(f"  {line.strip()}")
