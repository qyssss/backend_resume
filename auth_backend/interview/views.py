import os
import io
import requests
import pdfplumber
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

# 从环境变量获取 API 密钥
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-3f843c1b731642809c76190689ba9892")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = """
You are a professional interviewer conducting a mock interview for a job candidate. The user has uploaded their resume. You must:
1. Carefully analyze the resume content (education, work experience, skills, etc.)
2. Ask questions relevant to the resume
3. Progress from basic to in-depth questions
4. Ask only one question at a time
5. Avoid repeating questions
6. Ask follow-up questions based on the candidate's answers
7. Maintain a professional and friendly attitude
8. Provide constructive feedback at the end of the interview

You must conduct the entire interview in English.
"""

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        raise Exception(f"PDF parsing failed: {str(e)}")

def generate_question(resume_text: str, conversation_history: list) -> str:
    """Generate interview question using DeepSeek API"""
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if resume_text:
            messages.append({
                "role": "system",
                "content": f"Candidate's resume content:\n{resume_text[:3000]}"
            })

        messages.extend(conversation_history)
        messages.append({
            "role": "user",
            "content": "Generate the next interview question in English based on the resume and conversation history. Ask only one question."
        })

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }

        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(
                f"DeepSeek API request failed: {response.status_code} - {response.text}"
            )

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        raise Exception(f"Question generation failed: {str(e)}")


class UploadResumeView(APIView):
    parser_classes = [MultiPartParser]

    @csrf_exempt
    def post(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=400)

        file = request.FILES['file']
        if not file.name.endswith('.pdf'):
            return Response({"error": "Only PDF files are supported"}, status=400)

        try:
            content = file.read()
            resume_text = extract_text_from_pdf(content)
            return Response({"message": resume_text})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GenerateQuestionView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        try:
            resume_text = request.data.get('resume_text', '')
            conversation = request.data.get('conversation', [])

            question = generate_question(resume_text, conversation)
            return Response({"message": question})
        except Exception as e:
            return Response({"message": "", "error": str(e)}, status=500)


def health_check(request):
    """Health check endpoint"""
    return JsonResponse({"status": "healthy"})