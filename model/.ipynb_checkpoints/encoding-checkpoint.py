import os

from model.retinaface import Retinaface

'''
在更换facenet网络后一定要重新进行人脸编码，运行encoding.py。
'''
def encode_face_dataset():
    retinaface = Retinaface(1)

    list_dir = os.listdir("model/face_dataset")
    image_paths = []
    names = []
    for name in list_dir:
        path = "model/face_dataset/" + name
        if os.path.isfile(path):
            image_paths.append(path)
            names.append(name.split("_")[0])

    retinaface.encode_face_dataset(image_paths,names)
