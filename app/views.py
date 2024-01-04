import time
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.files.base import ContentFile
from app.models import *
from PIL import Image
import cv2
import io
import base64
import bcrypt
import base64
import jwt
from datetime import datetime, timedelta
from model.retinaface import Retinaface
import os
import numpy as np
import threading
camera = None

def index(request):
    if request.method == 'GET':
        return render(request, 'index.html')

class VideoCapture:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.start()

    def update(self):
        while self.running:
            self.ret, self.frame = self.cap.read()

    def read(self):
        return self.ret, self.frame

    def isOpened(self):
        return self.cap.isOpened()

    def stop(self):
        self.running = False
        self.thread.join()

    def release(self):
        self.stop()
        self.cap.release()

def gen(cam):
    global camera
    camera = cam
    retinaface = Retinaface()
    fps = 0.0
    while True:
        if camera is None or not camera.isOpened():
            break
        t1 = time.time()
        ref, frame = camera.read()
        if not ref:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detected_frame = retinaface.detect_image(frame)
        frame = np.array(detected_frame['image'])
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        fps = (fps + (1./(time.time()-t1))) / 2
        frame = cv2.putText(frame, "fps= %.2f" % (
            fps), (0, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        ret, jpeg = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')


def faceAnalyze(request):
    global camera
    url = request.GET.get('url')
    print(url)
    camera = VideoCapture(url)
    return StreamingHttpResponse(gen(camera), content_type='multipart/x-mixed-replace; boundary=frame')

def stopCamera(request):
    global camera
    if request.method == 'POST':
        if camera is not None:
            camera.release()
            camera = None
        return JsonResponse({'status': 0, 'message': '关闭摄像头成功'}, json_dumps_params={'ensure_ascii': False})

        
'''
    注册用户
    @param username String 用户名
    @param password String 密码
'''


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if User.objects.filter(username=username).first() is not None:
            return JsonResponse({'status': 1, 'message': '用户名已被注册'}, json_dumps_params={'ensure_ascii': False})
        else:
            password = bcrypt.hashpw(password.encode(
                'utf-8'), bcrypt.gensalt(prefix=b'2a')).decode('utf-8')
            User.objects.create(username=username, password=password)
            return JsonResponse({'status': 0, 'message': '注册成功'}, json_dumps_params={'ensure_ascii': False})


'''
    登陆
    @param username String 用户名
    @param password String 密码
'''


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = User.objects.filter(username=username).first()
        if user is None:
            return JsonResponse({'status': 1, 'message': '用户名不存在'}, json_dumps_params={'ensure_ascii': False})
        elif bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            payload = {
                'user_id': user.id,
                'exp': datetime.utcnow() + timedelta(days=1)
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            return JsonResponse({'status': 0, 'message': '登陆成功', 'token': token}, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({'status': 1, 'message': '输入密码错误'}, json_dumps_params={'ensure_ascii': False})

# 根据username获取用户信息


def getUserInfo(request):
    if request.method == 'GET':
        username = request.GET.get('username')
        user = User.objects.filter(username=username).first()
        if user is None:
            return JsonResponse({'status': 1, 'message': '用户名不存在'}, json_dumps_params={'ensure_ascii': False})
        else:
            user_data = {
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'email': user.email,
            }
            return JsonResponse({'status': 0, 'message': '获取用户信息成功', 'data': user_data}, json_dumps_params={'ensure_ascii': False})


# 根据用户id修改用户昵称和邮箱


def updateUserInfo(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        nickname = request.POST.get('nickname')
        email = request.POST.get('email')
        user = User.objects.filter(id=id).first()
        if user is None:
            return JsonResponse({'status': 1, 'message': '用户不存在'}, json_dumps_params={'ensure_ascii': False})
        else:
            user.nickname = nickname
            user.email = email
            user.save()
            return JsonResponse({'status': 0, 'message': '修改用户信息成功'}, json_dumps_params={'ensure_ascii': False})

# 根据用户id修改用户密码


def updateUserPassword(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        user = User.objects.filter(id=id).first()
        if user is None:
            return JsonResponse({'status': 1, 'message': '用户不存在'}, json_dumps_params={'ensure_ascii': False})
        elif bcrypt.checkpw(old_password.encode('utf-8'), user.password.encode('utf-8')):
            user.password = bcrypt.hashpw(new_password.encode(
                'utf-8'), bcrypt.gensalt(prefix=b'2a')).decode('utf-8')
            user.save()
            return JsonResponse({'status': 0, 'message': '修改密码成功'}, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({'status': 1, 'message': '原密码错误'}, json_dumps_params={'ensure_ascii': False})


def updataImage(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        image_data = request.POST.get('image')
        if image_data is None:
            return JsonResponse({'status': 1, 'message': '缺少必要的参数'}, json_dumps_params={'ensure_ascii': False})
        # Decode the base64 image data
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        # Delete the original file
        if default_storage.exists('model/face_dataset/' + name + '.' + ext):
            default_storage.delete(
                'model/face_dataset/' + name + '.' + ext)

        # Save the new file
        fs = FileSystemStorage()
        filename = fs.save('model/face_dataset/' +
                           name + '.' + ext, data)
        avatar_path = fs.url(filename)

        retinaface = Retinaface(1)
        list_dir = os.listdir("model/face_dataset")
        image_paths = []
        names = []
        for name in list_dir:
            path = "model/face_dataset/" + name
            if os.path.isfile(path):
                image_paths.append(path)
                names.append(name.split("_")[0])

        retinaface.encode_face_dataset(image_paths, names)
        return JsonResponse({'status': 0, 'message': '上传图像成功'}, json_dumps_params={'ensure_ascii': False})



