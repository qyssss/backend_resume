# views.py
import os
import json
import requests
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from common.firebase_utils import get_jobs_collection, get_resume_collection
from resume.views import ResumeBaseView
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# DeepSeek API配置
from auth_backend import settings

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-3f843c1b731642809c76190689ba9892")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

class JobRecommendationAPIView(ResumeBaseView):
    def post(self, request):
        try:
            # 获取用户简历
            doc_ref = self.get_user_resume_doc()
            resume_data = self.get_resume_data(doc_ref)

            # 获取岗位数据（限制数量以提高性能）
            jobs = []
            jobs_ref = get_jobs_collection() # 限制为100个岗位
            for doc in jobs_ref.stream():
                job = doc.to_dict()
                # 确保ID是字符串（Firestore文档ID）
                job['id'] = doc.id
                jobs.append(job)

            if not jobs:
                return Response(
                    {"error": "No jobs available for recommendation"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 检查缓存
            cache_key = f"job_recommendations_{self.user_id}"
            cached_result = cache.get(cache_key)

            if cached_result is not None:
                print("有缓存")
                return Response(cached_result)

            # 构建提示
            prompt = self.build_prompt(resume_data, jobs)

            # 调用DeepSeek API
            recommendations = self.call_deepseek_api(prompt)

            # 处理推荐结果
            recommended_jobs = self.process_recommendations(recommendations, jobs)

            # 将结果存入缓存
            cache.set(cache_key, recommended_jobs, timeout=settings.CACHE_TTL)
            print('新缓存')

            return Response(recommended_jobs)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def build_prompt(self, resume_data, jobs):
        """构建DeepSeek提示"""
        # 提取简历关键信息
        resume_info = {
            "skills": resume_data.get("skills", []),
            "experience": resume_data.get("experience", "Not specified"),
            "education": resume_data.get("education", "Not specified"),
            "honors": resume_data.get("honors", "Not specified"),
            "preferred_location": resume_data.get("preferred_location", "Not specified"),
            "expected_salary": resume_data.get("expected_salary", "Not specified")
        }

        # 格式化简历信息
        resume_str = json.dumps(resume_info, indent=2, ensure_ascii=False)

        # 格式化岗位信息
        jobs_str = "[\n"
        for job in jobs:
            job_info = {
                "id": job['id'],
                "title": job.get('title', ''),
                "company": job.get('company', ''),
                "location": job.get('location', ''),
                "salary": job.get('salary', ''),
                "required_skills": job.get('skills', []),
                "required_experience": job.get('experience', ''),
                "required_education": job.get('education', ''),
                "description": job.get('description', '')
            }
            jobs_str += f"  {json.dumps(job_info, ensure_ascii=False)},\n"
        jobs_str = jobs_str.rstrip(",\n") + "\n]"

        # 构建完整提示
        prompt = f"""
        你是一个专业的职业顾问，需要根据用户的简历信息，从可用岗位中推荐最匹配的3-5个岗位。
        请仔细分析用户的技能、经验和教育背景，找出最符合的岗位。
        
        ===== 用户简历信息 =====
        {resume_str}
        
        ===== 可用岗位列表 =====
        {jobs_str}
        
        ===== 任务要求 =====
        1. 请推荐3-5个最匹配的岗位
        2. 为每个推荐岗位提供:
           - id: 岗位ID (字符串)
           - matchScore: 匹配度评分 (0-100的整数)
           - reason: 推荐理由 (1-2句话)
        3. 匹配度评分应基于技能匹配度、经验匹配度、教育匹配度和地点匹配度
        4. 推荐理由应简洁明了，说明为什么这个岗位适合用户
        
        ===== 输出格式 =====
        请严格返回JSON格式的数组，每个元素是一个对象，包含以下字段:
        [
          {{
            "id": "岗位ID",
            "matchScore": 85,
            "reason": "您的Java技能与岗位要求高度匹配，且工作经验符合要求"
          }},
          {{
            "id": "岗位ID",
            "matchScore": 78,
            "reason": "您的教育背景与岗位要求一致，技能部分匹配"
          }}
        ]
        
        重要提示:
        1. 只返回JSON数组，不要包含任何其他内容
        2. 确保JSON格式完全正确
        3. 岗位ID必须与输入中的完全一致
        """
        # 构建完整英文提示
        prompt = f"""
        You are a professional career advisor. Your task is to recommend 3-5 most suitable jobs from the available positions based on the user's resume. 
        Please carefully analyze the user's skills, experience and education background to find the best matches.
        
        ===== User Resume Information =====
        {resume_str}
        
        ===== Available Job Positions =====
        {jobs_str}
        
        ===== Task Requirements =====
        1. Recommend 3-5 most suitable jobs
        2. For each recommended job, provide:
           - id: Job ID (string)
           - matchScore: Matching score (integer between 0-100)
           - reason: Recommendation reason (1-2 sentences in English)
        3. The matching score should be based on:
           - Skills match (40%)
           - Experience match (30%)
           - Education match (30%)
        4. The recommendation reason should be concise and explain why this job is suitable for the user
        
        ===== Output Format =====
        Return ONLY a JSON array with the following structure:
        [
          {{
            "id": "job_id_1",
            "matchScore": 85,
            "reason": "Your Java skills perfectly match the job requirements and your experience aligns with the position."
          }},
          {{
            "id": "job_id_2",
            "matchScore": 78,
            "reason": "Your educational background is ideal for this role and your skills are a strong match."
          }}
        ]
        
        Important Notes:
        1. Return ONLY the JSON array, no other content
        2. Ensure the JSON format is strictly correct
        3. Job IDs must match exactly with the input data
        4. Reason must be in English
        """

        return prompt.strip()

    def call_deepseek_api(self, prompt):
        """调用DeepSeek API获取推荐（全英文）"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional career advisor. Think and respond in English."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.4,  # 降低随机性，提高准确性
            "max_tokens": 3000,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        # 尝试解析JSON内容
        try:
            # 直接尝试解析
            return json.loads(content)
        except json.JSONDecodeError as e:
            # 尝试提取JSON部分
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            # 如果所有尝试都失败，记录完整响应
            raise ValueError("Failed to parse DeepSeek JSON response")

    def process_recommendations(self, recommendations, all_jobs):
        """处理推荐结果，构建最终响应（全英文）"""
        # 创建ID到岗位的映射
        job_map = {job['id']: job for job in all_jobs}

        recommended_jobs = []

        # 确保recommendations是列表
        if not isinstance(recommendations, list):
            recommendations = []

        for rec in recommendations:
            if not isinstance(rec, dict):
                continue

            job_id = rec.get('id')
            match_score = rec.get('matchScore', 0)
            reason = rec.get('reason', '')

            if not job_id:
                continue

            job = job_map.get(job_id)
            if not job:
                continue

            # 构建响应对象（符合接口要求）
            job_rec = {
                "id": job_id,  # 保持字符串ID
                "title": job.get('title', ''),
                "company": job.get('company', ''),
                "location": job.get('location', ''),
                "salary": job.get('salary', ''),
                "matchScore": match_score,
                "tags": job.get('skills', []),
                "reason": reason,  # 英文理由
                "description": job.get('description', '')
            }

            recommended_jobs.append(job_rec)

        # 按匹配度排序
        recommended_jobs.sort(key=lambda x: x['matchScore'], reverse=True)

        return recommended_jobs


class JobAnalysisAPIView(ResumeBaseView):
    def post(self, request, format=None):
        try:
            # 获取JD文本
            job_description = request.data.get('jobDescription')

            if not job_description:
                return Response(
                    {"error": "Missing job_description in request"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 获取用户简历
            doc_ref = self.get_user_resume_doc()
            resume_data = self.get_resume_data(doc_ref)

            # 构建全英文提示
            prompt = self.build_english_prompt(resume_data, job_description)

            # 调用DeepSeek API
            analysis_result = self.call_deepseek_api(prompt)

            # 处理分析结果
            report = self.process_analysis_result(analysis_result)

            return Response(report)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def build_english_prompt(self, resume_data, job_description):
        """构建全英文提示"""
        # 提取简历关键信息（英文）
        resume_info = {
            "skills": resume_data.get("skills", []),
            "experience": resume_data.get("experience", "Not specified"),
            "education": resume_data.get("education", "Not specified"),
            "honors": resume_data.get("honors", "Not specified"),
            "projects": resume_data.get("projects", []),
            "summary": resume_data.get("summary", "")
        }

        # 构建完整英文提示
        prompt = f"""
        You are a professional career advisor. Your task is to analyze how well a candidate's resume matches a given job description (JD). 
        Please carefully compare the resume information with the job requirements and provide a detailed matching analysis.
        
        ===== Job Description =====
        {job_description}
        
        ===== Candidate Resume Information =====
        {json.dumps(resume_info, indent=2, ensure_ascii=False)}
        
        ===== Task Requirements =====
        1. Provide an overall match score (0-100) based on how well the resume matches the JD requirements.
        2. Clearly list the strengths - areas where the resume matches the JD requirements (skills, experience, etc.).
        3. Clearly list the gaps - areas where the resume is missing or weak compared to the JD requirements.
        4. For each gap, provide practical suggestions on how to improve the resume.
        5. Provide a brief summary of the analysis.
        
        ===== Output Format =====
        Return ONLY a JSON object with the following structure:
        {{
          "matchScore": 85,
          "summary": "Overall, the candidate has strong technical skills but lacks specific industry experience.",
          "strengths": [
            "5+ years of Python development experience matches the required seniority level",
            "Experience with Django and Flask frameworks aligns with backend requirements"
          ],
          "gaps": [
            "Lacks AWS cloud experience - suggested adding AWS certification or project experience",
            "No experience with microservices architecture - suggested highlighting relevant distributed systems projects"
          ]
        }}
        
        Important Notes:
        1. Return ONLY the JSON object, no other content
        2. Ensure the JSON format is strictly correct
        3. Match score should be an integer between 0-100
        4. Strengths and gaps should be concise bullet points
        5. Suggestions should be actionable and practical
        """

        return prompt.strip()

    def call_deepseek_api(self, prompt):
        """调用DeepSeek API获取分析报告（全英文）"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional career advisor specializing in resume-JD matching analysis. Think and respond in English."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # 降低随机性，提高准确性
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        # 尝试解析JSON内容
        try:
            # 直接尝试解析
            return json.loads(content)
        except json.JSONDecodeError as e:

            # 尝试提取JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            # 如果所有尝试都失败，记录完整响应
            raise ValueError("Failed to parse DeepSeek JSON response")

    def process_analysis_result(self, analysis_result):
        """处理分析结果，构建最终响应"""
        # 确保分析结果包含所有必需字段
        match_score = analysis_result.get('matchScore', 0)
        summary = analysis_result.get('summary', 'No summary provided')
        strengths = analysis_result.get('strengths', [])
        gaps = analysis_result.get('gaps', [])

        # 构建响应对象
        report = {
            "matchScore": match_score,
            "summary": summary,
            "strengths": strengths,
            "gaps": gaps
        }

        return report
