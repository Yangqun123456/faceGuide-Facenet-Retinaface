# 使用官方Python镜像作为基础镜像
FROM python:3.8

# 设置工作目录
WORKDIR /usr/src/app

# 设置环境变量
# PYTHONDONTWRITEBYTECODE: 防止Python写.pyc文件到磁盘
# PYTHONUNBUFFERED: 确保我们的Python输出直接在终端中打印，而不用再进行缓存
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装项目依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 将当前目录下的所有文件（除了.dockerignore排除的路径），复制到容器的/app目录下
COPY . .

# 暴露端口，使得Docker容器的应用可以被访问，假设你的应用运行在8000端口
EXPOSE 6008

# 运行应用
CMD ["python", "manage.py", "runserver", "0.0.0.0:6008"]