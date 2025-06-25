import json
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ResumeSerializer
#from .common.firebase_utils import get_resume_collection
from common.firebase_utils import get_resume_collection
from firebase_admin import firestore
from firebase_admin.exceptions import FirebaseError
import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from common.parsers import PlainTextJSONParser  # 导入自定义解析器
import requests
import os
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
SM_MS_API_URL = "https://sm.ms/api/v2/upload"
SM_MS_TOKEN = os.environ.get('SM_MS_TOKEN', 'IFBldSrcoBITPadg7v6HSJfw3RekT6Am')
# 新增简单用户类
class SimpleUser:
    def __init__(self, uid):
        self.uid = uid
        self.is_authenticated = True  # 关键属性

class JWTAuthentication:
    """自定义 JWT 认证中间件"""
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                return None

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )

            # 返回用户对象而非字典
            user = SimpleUser(uid=payload.get('user_id'))
            return (user, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')


class ResumeBaseView(APIView):
    # 添加以下解析器配置
    parser_classes = [JSONParser,FormParser, MultiPartParser, PlainTextJSONParser]

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @property
    def user_id(self):
        """获取当前用户ID"""
        return self.request.user.uid

    def get_user_resume_doc(self):
        """获取当前用户的简历文档引用"""
        print(self.user_id)
        resume_collection = get_resume_collection()
        return resume_collection.document(self.user_id)

    def get_resume_data(self, doc_ref):
        """获取简历数据"""
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None

# 简历保存
class SaveResumeView(ResumeBaseView):
    """保存简历（创建或更新）"""

    def post(self, request):
        doc_ref = self.get_user_resume_doc()

        # 准备简历数据
        resume_data = {
            "user_id": self.user_id,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "personal": request.data.get('personal', {}),
            "skills": request.data.get('skills', {}),
            "education": request.data.get('education', []),
            "experiences": request.data.get('experiences', []),
            "honors": request.data.get('honors', []),
            "selfEvaluation": request.data.get('selfEvaluation', '')
        }

        # 验证数据
        serializer = ResumeSerializer(data=resume_data)
        if serializer.is_valid():
            try:
                # 保存或更新简历
                doc_ref.set(serializer.validated_data)
                cache.delete(f'job_recommendations_{self.user_id}')
                return Response({'message': '简历保存成功'}, status=status.HTTP_200_OK)
            except FirebaseError as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 简历获取
class GetResumeView(ResumeBaseView):
    """获取简历"""

    def get(self, request):
        try:
            doc_ref = self.get_user_resume_doc()
            resume_data = self.get_resume_data(doc_ref)

            if resume_data:
                # 移除内部字段
                resume_data.pop('user_id', None)
                resume_data.pop('updated_at', None)
                return Response({
                    "status": "success",
                    "code": status.HTTP_200_OK,
                    "data": resume_data
                })
            return Response({'message': '未找到简历'}, status=status.HTTP_404_NOT_FOUND)
        except FirebaseError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 简历更新
class UpdateResumeView(ResumeBaseView):
    """更新简历"""

    def put(self, request):
        doc_ref = self.get_user_resume_doc()

        # 检查简历是否存在
        if not self.get_resume_data(doc_ref):
            return Response({'error': '请先创建简历'}, status=status.HTTP_404_NOT_FOUND)

        # 准备更新数据
        update_data = {
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        # 只更新提供的字段
        for field in ['personal', 'skills', 'education', 'experiences', 'honors', 'selfEvaluation']:
            if field in request.data:
                update_data[field] = request.data[field]

        try:
            # 执行更新
            doc_ref.update(update_data)
            cache.delete(f'job_recommendations_{self.user_id}')
            return Response({'message': '简历更新成功'})
        except FirebaseError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 简历删除
class DeleteResumeView(ResumeBaseView):
    """删除当前用户的简历"""

    def delete(self, request):
        try:
            doc_ref = self.get_user_resume_doc()
            # 检查文档是否存在
            if not doc_ref.get().exists:
                return Response({'message': '简历不存在'}, status=status.HTTP_404_NOT_FOUND)

            # 删除文档
            doc_ref.delete()
            cache.delete(f'job_recommendations_{self.user_id}')
            return Response({
                'status': 'success',
                'message': '简历删除成功',
                'code': status.HTTP_200_OK
            })

        except FirebaseError as e:
            return Response({
                'status': 'error',
                'message': f'删除失败: {str(e)}',
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR
            })

# 简历图片上传
class ResumePhotoUploadAPIView(APIView):
    def post(self, request, format=None):
        # 检查文件是否存在
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        image_file = request.FILES['file']
        # 准备请求到SM.MS图床
        files = {'smfile': (image_file.name, image_file, image_file.content_type)}
        headers = {'Authorization': SM_MS_TOKEN}
        try:
            # 发送到SM.MS API
            response = requests.post(SM_MS_API_URL, files=files, headers=headers)
            response_data = response.json()

            # 检查图床返回结果
            if response.status_code == 200:
                if response_data.get('success'):
                    image_url = response_data['data']['url']
                    return Response({'url': image_url}, status=status.HTTP_200_OK)

                # 处理图片已存在的情况
                if response_data.get('code') == 'image_repeated':
                    # 从错误消息中提取存在的URL
                    image_url = response_data['images']
                    if image_url:
                        return Response({'url': image_url}, status=status.HTTP_200_OK)

            # 处理SM.MS错误响应
            error_msg = response_data.get('message', 'Unknown error from SM.MS')
            return Response(
                {'error': f'SM.MS upload failed: {error_msg}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except requests.exceptions.RequestException as e:
            return Response(
                {'error': f'Network error: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except ValueError as e:  # JSON解析错误
            return Response(
                {'error': f'Invalid response from SM.MS: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            return Response(
                {'error': f'Server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# 新增简历优化接口（英语版）
class OptimizeResumeView(ResumeBaseView):
    """使用DeepSeek大模型API优化简历（英语）"""

    # DeepSeek API配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-3f843c1b731642809c76190689ba9892")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

    def post(self, request):
        try:
            # 1. 获取用户简历数据
            doc_ref = self.get_user_resume_doc()
            resume_data = self.get_resume_data(doc_ref)

            if not resume_data:
                return Response({'error': 'Resume data not found'}, status=status.HTTP_404_NOT_FOUND)

            # 2. 准备英语优化提示词
            prompt = self._create_english_optimization_prompt(resume_data)

            # 3. 调用DeepSeek API进行优化
            optimized_content = self._call_deepseek_api(prompt)

            # 4. 解析优化结果
            optimized_resume = self._parse_optimized_resume(optimized_content, resume_data)

            # 5. 验证优化后的数据
            serializer = ResumeSerializer(data=optimized_resume)
            if not serializer.is_valid():
                return Response({
                    'error': 'Optimized resume format is invalid',
                    'details': serializer.errors
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 6. 返回优化后的简历给前端
            return Response({
                'status': 'success',
                'message': 'Resume optimized successfully',
                'data': serializer.validated_data
            })

        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'Failed to connect to DeepSeek API: {str(e)}'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except FirebaseError as e:
            return Response({
                'error': f'Database error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError as e:
            return Response({
                'error': f'Failed to parse optimized resume: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'error': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_english_optimization_prompt(self, resume_data):
        """创建英语优化提示词"""
        # 提取简历各部分内容
        personal = resume_data.get("personal", {})
        skills = resume_data.get("skills", {})
        education = resume_data.get("education", [])
        experiences = resume_data.get("experiences", [])
        honors = resume_data.get("honors", [])
        self_eval = resume_data.get("selfEvaluation", "")

        # 构建英语提示词
        prompt = f"""
        You are a professional resume optimization expert. Please optimize the following resume information in English:
        
        === Personal Information ===
        Name: {personal.get('name', '')}
        Gender: {personal.get('gender', '')}
        Age: {personal.get('age', '')}
        Degree: {personal.get('degree', '')}
        Phone: {personal.get('phone', '')}
        Email: {personal.get('email', '')}
        Photo: {personal.get('photo', '')} 
        
        
        === Skills ===
        Proficient: {', '.join(skills.get('proficient', []))}
        Familiar: {', '.join(skills.get('familiar', []))}
        
        === Education ===
        {self._format_education_english(education)}
        
        === Work/Project Experience ===
        {self._format_experiences_english(experiences)}
        
        === Honors & Awards ===
        {self._format_honors_english(honors)}
        
        === Self-Evaluation ===
        {self_eval}
        
        Optimization Requirements:
        1. Keep the original JSON structure and field names
        2. Optimize all content in professional English
        3. Use industry-standard terminology and action verbs
        4. Quantify achievements where possible (e.g., "increased efficiency by 20%")
        5. Apply STAR method (Situation, Task, Action, Result) to work experiences
        6. Keep self-evaluation concise (max 150 words), highlighting core competencies
        7. Maintain original proper nouns (names, universities, companies) but translate descriptions
        8. Ensure all dates and numbers follow international standards (e.g., "May 2022", not "2022.05")
        
        
        Important: Return only a valid JSON object with the following exact structure:
    {{
        "personal": {{
            "name": "string",
            "gender": "string",
            "age": "string",
            "degree": "string",
            "phone": "string",
            "email": "string",
            "photo": "string"
        }},
        "skills": {{
            "proficient": ["string", "..."],
            "familiar": ["string", "..."]
        }},
        "education": [
            {{
                "school": "string",
                "major": "string",
                "degree": "string",
                "score": "string"
            }},
            ...
        ],
        "experiences": [
            {{
                "type": "string",
                "name": "string",
                "company": "string",
                "period": "string",
                "content": "string",
                "result": "string"
            }},
            ...
        ],
        "honors": [
            {{
                "type": "string",
                "title": "string",
                "date": "string",
                "description": "string"
            }},
            ...
        ],
        "selfEvaluation": "string"
    }}
    
    Do not include any additional text, explanations, or markdown formatting. 
    Only return the pure JSON object.
        """

        return prompt

    def _format_education_english(self, education_list):
        """格式化教育背景（英语）"""
        formatted = []
        for edu in education_list:
            formatted.append(
                f"School: {edu.get('school', '')}, Major: {edu.get('major', '')}, "
                f"Degree: {edu.get('degree', '')}, GPA/Score: {edu.get('score', '')}"
            )
        return "\n".join(formatted) if formatted else "None"

    def _format_experiences_english(self, experiences):
        """格式化工作经历（英语）"""
        formatted = []
        for exp in experiences:
            formatted.append(
                f"Type: {exp.get('type', '')}, Position: {exp.get('name', '')}, "
                f"Company: {exp.get('company', '')}, Period: {exp.get('period', '')}\n"
                f"Responsibilities: {exp.get('content', '')}\n"
                f"Achievements: {exp.get('result', '')}"
            )
        return "\n\n".join(formatted) if formatted else "None"

    def _format_honors_english(self, honors):
        """格式化荣誉奖项（英语）"""
        formatted = []
        for honor in honors:
            formatted.append(
                f"Type: {honor.get('type', '')}, Award: {honor.get('title', '')}, "
                f"Date: {honor.get('date', '')}, Description: {honor.get('description', '')}"
            )
        return "\n".join(formatted) if formatted else "None"

    def _call_deepseek_api(self, prompt):
        """调用DeepSeek API（英语优化）"""
        headers = {
            "Authorization": f"Bearer {self.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a professional resume optimization expert. Optimize resumes in professional English while maintaining the original JSON structure."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
            "top_p": 0.9
        }

        response = requests.post(
            self.DEEPSEEK_API_URL,
            json=payload,
            headers=headers,
            timeout=60  # 设置较长超时时间
        )

        if response.status_code != 200:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            raise ValueError(f"DeepSeek API error: {response.status_code} - {error_msg}")

        # 提取API响应内容
        return response.json()["choices"][0]["message"]["content"]

    def _parse_optimized_resume(self, content, original_resume):
        """
        解析优化后的简历内容
        注意：由于大模型可能返回非纯JSON内容，我们需要提取JSON部分
        """
        try:
            # 尝试直接解析为JSON
            return json.loads(content)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("Unable to extract JSON data from response")

            try:
                return json.loads(content[start_idx:end_idx])
            except json.JSONDecodeError:
                # 作为最后手段，尝试修复常见问题
                fixed_content = self._fix_json_issues(content[start_idx:end_idx])
                try:
                    return json.loads(fixed_content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"JSON parsing failed: {str(e)}")

    def _fix_json_issues(self, json_str):
        """尝试修复常见的JSON格式问题"""
        # 修复单引号问题
        json_str = json_str.replace("'", '"')

        # 修复缺少引号的字段名
        json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)

        # 修复尾随逗号
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # 修复布尔值问题
        json_str = json_str.replace(": true", ': "true"').replace(": false", ': "false"')

        return json_str


