# import_jobs_to_firebase.py
import csv
import firebase_admin
from firebase_admin import credentials, firestore
import chardet  # 用于检测文件编码

def detect_encoding(file_path):
    """检测文件的编码格式"""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def import_jobs_from_csv(csv_file_path):
    # 初始化Firebase应用
    cred = credentials.Certificate("jobfind-53c9b-firebase-adminsdk-fbsvc-70e81f3842.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # 检测文件编码
    encoding = detect_encoding(csv_file_path)
    print(f"检测到文件编码: {encoding}")

    # 读取CSV文件
    with open(csv_file_path, 'r', encoding=encoding, errors='replace') as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader):
            # 清理和转换数据
            job_data = {
                'id': index + 1,  # 生成自增ID
                'title': row['job_title'],
                'company': row['job_company'],
                'location': row['job_location'].replace('?', '/'),
                'salary': row['job_salary_range'].replace('?', '-'),
                'description': f"{row['job_title']} at {row['job_company']}",
                'category': row['category'],
                'experience': row['job_experience'],
                'education': row['job_education'],
                'skills': [s.strip() for s in row['job_skills'].split(',') if s.strip()],
                'industry': row['job_industry'],
                'welfare': row['job_welfare'],
                'scale': row['job_scale'],
                'create_time': row['create_time']
            }
            # 添加到Firestore
            db.collection('jobs').document(str(job_data['id'])).set(job_data)
            print(f"导入职位 #{job_data['id']}: {job_data['title']}")

if __name__ == '__main__':
    # 安装chardet: pip install chardet
    import_jobs_from_csv('job_info.csv')