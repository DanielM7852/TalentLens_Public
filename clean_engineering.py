import pdfplumber
import re 
import os 

def clean_text(text): 
    text = text.lower()
    text = re.sub(r'http\S+\s*', ' ', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', ' ', text)
    text = re.sub(r'\b\d{10,}\b', ' ', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text 

with pdfplumber.open("data/resume-dataset/data/data/ENGINEERING/10030015.pdf") as pdf:
    raw_content = ""
    for page in pdf.pages: 
        raw_content += page.extract_text()
    
    clean_content = clean_text(raw_content)
    
    #print(clean_content[:500]) #tester 