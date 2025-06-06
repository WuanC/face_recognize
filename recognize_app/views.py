import json
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch.nn.functional as F
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from PIL import Image
from attendance_app.models import SubjectDate, CustomUser, StudentAttendance
from attendance_app.permissions import IsTeacher, IsStudent
from rest_framework.permissions import IsAuthenticated

device = 'cuda' if torch.cuda.is_available() else 'cpu'
THRESHOLD = 0.8

mtcnn = MTCNN(keep_all=True, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

with open(r'E:\face_recognize\recognize_app\centroids.json', 'r') as f:
    cent_dict = json.load(f)

names = list(cent_dict.keys())
centroids = torch.stack([F.normalize(torch.tensor(cent_dict[n]), dim=0) for n in names]).to(device)


class FaceRecognitionAPIView(APIView):

    def post(self, request):
        uploaded_file = request.FILES.get("image")
        subject_date_id = request.data.get("subject_date_id")

        if not uploaded_file:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject_date = SubjectDate.objects.get(id=subject_date_id)
        except SubjectDate.DoesNotExist:
            return Response({"boxes": [], "names": [], "scores": [], "attended_users": []}, status=status.HTTP_200_OK)

        if not subject_date.status:
            return Response({"boxes": [], "names": [], "scores": [], "attended_users": []}, status=status.HTTP_200_OK)

        try:
            image = Image.open(uploaded_file).convert('RGB')
            rgb_image = np.array(image)
        except Exception:
            return Response({"error": "Invalid image file"}, status=status.HTTP_400_BAD_REQUEST)

        faces = mtcnn(rgb_image)
        boxes, _ = mtcnn.detect(rgb_image)

        results = {'boxes': [], 'names': [], 'scores': [], 'attended_users': []}
        attended_users = []

        if faces is not None and boxes is not None:
            if isinstance(faces, torch.Tensor):
                faces = [faces[i] for i in range(faces.shape[0])]

            batch = torch.stack(faces).to(device)
            with torch.no_grad():
                embs = F.normalize(model(batch))
                sims = embs @ centroids.T
                best_scores, best_idx = sims.max(1)

            for box, score, idx in zip(boxes, best_scores, best_idx):
                x1, y1, x2, y2 = map(int, box)
                name = "Unknown"

                if score >= THRESHOLD:
                    recognized_name = names[idx]
                    student = CustomUser.objects.filter(username=recognized_name).first()

                    if student:
                        # Kiểm tra xem student có trong danh sách điểm danh của buổi học này không
                        attendance = StudentAttendance.objects.filter(student=student, subject_date=subject_date).first()
                        if attendance:
                            if not attendance.status:
                                attendance.status = True
                                attendance.save()
                                name = student.username
                                attended_users.append(student.username)
                            else:
                                name = student.username + " OK"
                        else:
                            name = student.username + " (Not enrolled)"
                    else:
                        name = "Unknown"

                results['boxes'].append([x1, y1, x2, y2])
                results['names'].append(name)
                results['scores'].append(score.item())

            results['attended_users'] = attended_users
        else:
            return Response({"boxes": [], "names": [], "scores": [], "attended_users": []}, status=status.HTTP_200_OK)

        return Response(results, status=status.HTTP_200_OK)


@api_view(['POST'])
def upload_face(request):
    student_id = request.POST.get('student_id')
    image = request.FILES.get('image')

    if not student_id or not image:
        return Response({'error': 'Missing student_id or image'}, status=status.HTTP_400_BAD_REQUEST)

    # Lấy user theo student_id
    try:
        user = CustomUser.objects.get(id=student_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Lấy tên folder theo username
    folder_name = user.username.strip()

    base_dir = r'E:\face_recognize\media\dataset' 
    save_dir = os.path.join(base_dir, folder_name)
    os.makedirs(save_dir, exist_ok=True)

    # Lưu ảnh vào folder tương ứng
    image_path = os.path.join(save_dir, image.name)
    with open(image_path, 'wb+') as f:
        for chunk in image.chunks():
            f.write(chunk)

    return Response({'message': 'Image uploaded successfully'}, status=status.HTTP_200_OK)
