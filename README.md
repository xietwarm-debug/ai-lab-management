# AI Lab Management System

基于 Flask + Uni-App 的实验室预约与管理系统。

本系统实现了实验室预约、审批管理、失物招领、通知中心、审计日志等完整功能模块，
采用 JWT 双 Token 认证机制，并支持管理员权限控制与操作审计。

---

## 🛠 技术栈

### 前端
- Uni-App
- Vue 3
- SCSS
- 微信小程序构建

### 后端
- Python Flask
- PyMySQL
- flask-cors
- JWT（Access + Refresh Token 自实现）
- 内存级限流

### 数据库
- MySQL（数据库名：lab_mgmt）

---

## 📌 功能模块

### 账号系统
- 登录 / 注册
- Access Token + Refresh Token
- 修改密码
- 登出

### 权限体系
- student / admin 分权
- 管理员接口鉴权
- 操作审计日志

### 实验室管理
- 实验室创建 / 编辑 / 删除
- 实验室图片上传
- 实验室容量与设备管理

### 预约系统
- 创建预约
- 取消 / 改期
- 冲突检测
- 管理员审批
- 批量处理
- CSV 导出

### 失物招领
- 发布物品
- 认领申请
- 管理员审核
- 结案处理

### 通知中心
- 预约状态通知
- 认领状态通知

---

## 🏗 系统架构

前端（Uni-App）
        ↓
REST API
        ↓
Flask 后端
        ↓
MySQL 数据库

认证机制：
Access Token（短期） + Refresh Token（数据库持久化）

---

## 📂 项目结构
ai-lab-management
├── backend
│ ├── app.py
│ ├── uploads/
│ └── requirements.txt
├── frontend
│ ├── pages/
│ ├── common/
│ └── ...
└── README.md


---

## 🚀 本地运行方式

### 1️⃣ 启动后端

进入 backend 目录：

```bash
pip install -r requirements.txt
python app.py
默认运行：
http://0.0.0.0:5000

2️⃣ 启动前端

使用 HBuilderX 打开 frontend 目录：

运行到浏览器

或构建为微信小程序

API 默认地址：

http://127.0.0.1:5000

🗄 数据库说明

数据库名：

lab_mgmt

主要表：

user

lab

reservation

lost_found

auth_refresh_token

audit_log

🔐 安全设计

JWT 双 Token 机制

Refresh Token 数据库存储 + 轮换机制

接口鉴权装饰器 auth_required

登录/注册/刷新限流

审计日志记录关键操作

📊 后续优化方向

Docker 部署

统计报表完善

AI 预约推荐算法

图像相似检索（失物招领）

微服务拆分

👨‍💻 作者

xietwarm-debug


---

# 🔥 提升档次的 3 个加分项

## 1️⃣ 加系统截图（非常加分）

在仓库里建一个文件夹：


/docs/images


把系统截图放进去，然后在 README 里写：

```markdown
## 📷 系统截图

![首页](docs/images/home.png)
![管理员页面](docs/images/admin.png)