from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from docx import Document
import PyPDF2
import os
from io import BytesIO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def extract_cv_text(file: UploadFile) -> str:
    content = ""
    if file.filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file.file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                content += text + "\n"
    elif file.filename.endswith(".docx"):
        doc = Document(file.file)
        for para in doc.paragraphs:
            content += para.text + "\n"
    return content


def detect_language(text: str) -> str:
    lang_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a language expert."},
            {"role": "user", "content": f"What language is this CV written in?\n\n{text[:1000]}"}
        ],
        temperature=0,
        max_tokens=20
    )
    return lang_response.choices[0].message.content.strip()


def generate_cover_letter(cv_text: str, job_description: str, language: str, tone: str) -> str:
    prompt = f"""
Write the following in {language}:

Use a tone that is {tone.lower()}.

Use the CV and job description below to write a **tailored** and **personal** cover letter.
Use real strengths, courses, and experiences from the CV that are relevant to this job.
Reference specific responsibilities or values from the job description where appropriate.

Here is the CV:
{cv_text}

Here is the job description:
{job_description}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert in writing job applications tailored to each candidate."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message.content


@app.post("/generate")
async def generate(cv_file: UploadFile, job_description: str = Form(...), tone: str = Form(...)):
    cv_text = extract_cv_text(cv_file)
    language = detect_language(cv_text)
    letter = generate_cover_letter(cv_text, job_description, language, tone)
    return {"cover_letter": letter, "language": language}
