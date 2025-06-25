## 基础配置
### 1. 运行指令
``` 
  python -m venv myenv       # 创建名为myenv的虚拟环境
  source myenv/bin/activate  # Linux/Mac激活虚拟环境
  myenv\Scripts\activate     # Windows激活虚拟环境
  cd auth_backend
  pip install -r requirements.txt   #安装依赖包
  python manage.py runserver
```
### 2. 岗位信息导入数据库
``` 
  cd auth_backend
  python import_jobs_to_firebase.py 
```

### 3. FireBase 地址

https://console.firebase.google.com/project/jobfind-53c9b/firestore/databases/-default-/data/~2Fusers~2FVP3PNEhWD7taXaghAbWk

### 4. Redis安装
**windows环境**
https://blog.csdn.net/antma/article/details/79225084

## API 接口列表

### 1. 用户注册

注册新用户账户。

- **Endpoint**: `/users/register/`
- **Method**: `POST`
- **请求示例**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePass123!",
    "username": "john_doe"
  }
  ```

- **成功响应** (`HTTP 201 Created`):
  ```json
  {
    "message": "User created successfully"
  }
  ```

- **错误响应**:
    - `HTTP 400 Bad Request`: 请求参数错误或邮箱已被注册
      ```json
      {
        "error": "Email already exists"
      }
      ```
    - `HTTP 500 Internal Server Error`: 服务器内部错误

---

### 2. 用户登录

用户登录并获取访问令牌。

- **Endpoint**: `/users/login/`
- **Method**: `POST`
- **请求示例**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePass123!"
  }
  ```

- **成功响应** (`HTTP 200 OK`):
  ```json
  {
    "token": "eyJhbGciOiEF9.6OWYhg4vo2QX...",
    "user_id": "VP3PNEhWD7taXaghAbWk",
    "username": "testuser"
  }
  ```

- **错误响应**:
    - `HTTP 400 Bad Request`: 请求参数错误
      ```json
      {
        "error": "Email and password required"
      }
      ```
    - `HTTP 401 Unauthorized`: 密码错误或用户不存在
      ```json
      {
        "error": "Invalid credentials"
      }
      ```

---


