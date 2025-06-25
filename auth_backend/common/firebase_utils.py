import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("./jobfind-53c9b-firebase-adminsdk-fbsvc-e6bb9f2f45.json")
    firebase_app = firebase_admin.initialize_app(cred)
else:
    firebase_app = firebase_admin.get_app()

# 创建全局的 Firestore 客户端
db = firestore.client()

def get_resume_collection():
    """获取简历集合的引用"""
    return db.collection('resumes')

def get_users_collection():
    """获取用户集合的引用"""
    return db.collection('users')

def get_jobs_collection():
    """获取岗位集合的引用"""
    return db.collection('jobs')