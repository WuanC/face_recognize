import json
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch.nn.functional as F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
import io
from rest_framework.decorators import api_view
import os
from django.conf import settings
from attendance_app.models import SubjectDate, SubjectStudent, CustomUser, StudentAttendance;



# Cấu hình thiết bị
device = 'cuda' if torch.cuda.is_available() else 'cpu'
THRESHOLD = 0.8  # Ngưỡng nhận diện

# Khởi tạo mô hình MTCNN và InceptionResnetV1
mtcnn = MTCNN(keep_all=True, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Tải centroids (dữ liệu huấn luyện đã có)
with open('recognize_app/centroids.json', 'r') as f:
    cent_dict = json.load(f)

names = list(cent_dict.keys())
centroids = torch.stack([F.normalize(torch.tensor(cent_dict[n]), dim=0) for n in names]).to(device)

class FaceRecognitionAPIView(APIView):
    def post(self, request):
        uploaded_file = request.FILES.get("image")
        subject_date_id = request.data.get("subject_date_id")


        
        if not SubjectDate.objects.filter(id=subject_date_id).exists():
            return Response({
                "boxes": [],
                "names": "NF",
                "scores": [],
            }, status=200)

        if not uploaded_file:
            print("Không có ảnh được gửi lên.")  
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

        print(f"Đã nhận ảnh: {uploaded_file.name}")

        # Đọc ảnh từ file tải lên
        image = Image.open(uploaded_file)
        rgb_image = np.array(image.convert('RGB'))  # Chuyển ảnh sang RGB

        # Tìm các khuôn mặt trong ảnh
        faces = mtcnn(rgb_image)
        boxes, _ = mtcnn.detect(rgb_image)

        results = {'boxes': [], 'names': [], 'scores': []}

        if faces is not None and boxes is not None:
            if isinstance(faces, torch.Tensor):
                faces = [faces[i] for i in range(faces.shape[0])]

            batch = torch.stack(faces).to(device)
            with torch.no_grad():
                embs = F.normalize(model(batch))  # Tính toán embedding
                sims = embs @ centroids.T  # Tính cosine similarity
                best_scores, best_idx = sims.max(1)

            print(f"Phát hiện {len(boxes)} khuôn mặt.")

            for (box, score, idx) in zip(boxes, best_scores, best_idx):
                x1, y1, x2, y2 = map(int, box)
                if score >= THRESHOLD:
                    subject_date = SubjectDate.objects.get(id=subject_date_id)
                    if subject_date.status == False:
                        return Response({
                            "boxes": [],
                            "names": "NF",
                            "scores": [],
                            }, status=200)
                    student = CustomUser.objects.get(id=names[idx]) 
                    if not student:
                        name = "Unknown"
                    #attendance = StudentAttendance.objects.get(student=student, subject_date=subject_date)
                    attendance = StudentAttendance.objects.filter(student=student, subject_date=subject_date).first()
                    print(names[idx])
                    if attendance and attendance.status == False:
                        attendance.status = True
                        attendance.save()
                        name = student.first_name
                    elif attendance and attendance.status == True:
                        name = student.first_name + " OK"
                    else:
                        name = "Unknown"
                else:
                    name = "Unknown"

                print(f"Khuôn mặt tại [{x1}, {y1}, {x2}, {y2}] - Tên: {name} - Điểm: {score.item():.4f}")

                results['boxes'].append([x1, y1, x2, y2])
                results['names'].append(name)
                results['scores'].append(score.item())
        else:
            print("Không phát hiện được khuôn mặt nào.")

        return Response(results, status=status.HTTP_200_OK)
@api_view(['POST'])
def upload_face(request):
    student_id = request.POST.get('student_id')
    image = request.FILES.get('image')

    if not student_id or not image:
        return Response({'error': 'Missing student_id or image'}, status=status.HTTP_400_BAD_REQUEST)

    # Tạo thư mục lưu ảnh nếu chưa có
    save_dir = os.path.join(settings.MEDIA_ROOT, 'dataset', student_id)
    os.makedirs(save_dir, exist_ok=True)

    # Lưu ảnh
    image_path = os.path.join(save_dir, image.name)
    with open(image_path, 'wb+') as f:
        for chunk in image.chunks():
            f.write(chunk)

    return Response({'message': 'Image uploaded successfully'}, status=status.HTTP_200_OK)