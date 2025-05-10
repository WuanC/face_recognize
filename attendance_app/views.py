from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, Subject, SubjectDate, StudentAttendance, SubjectStudent
from .serializers import CustomUserSerializer, SubjectSerializer, SubjectDateSerializer, StudentAttendanceSerializer, SubjectStudentSerializer
from rest_framework import viewsets
from rest_framework.decorators import action

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

class SubjectStudentViewSet(viewsets.ModelViewSet):
    queryset = SubjectStudent.objects.all()
    serializer_class = SubjectStudentSerializer

class SubjectDateViewSet(viewsets.ModelViewSet):
    queryset = SubjectDate.objects.all()
    serializer_class = SubjectDateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject_date = serializer.save()

        subject = subject_date.subject

        subject_students = SubjectStudent.objects.filter(subject=subject)

        attendance_list = []
        for ss in subject_students:
            attendance = StudentAttendance.objects.create(
                student=ss.student,
                subject_date=subject_date,
                status=False  # Mặc định là vắng
            )
            attendance_list.append(attendance)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class StudentAttendanceViewSet(viewsets.ModelViewSet):
    queryset = StudentAttendance.objects.all()
    serializer_class = StudentAttendanceSerializer

class LoginView(viewsets.ViewSet):
    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        
        role = user.role
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': role,  
        })

class UserInfoViewSet(viewsets.ViewSet):
    #permission_classes = [IsAuthenticated]  
    def list(self, request, *args, **kwargs):
        user = request.user  

        user_info = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "avatar": user.avatar.url if user.avatar else None,
            "date_created": user.date_created,
        }

        return Response(user_info)
    
class TeacherSubjectsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubjectSerializer
    #permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return Subject.objects.filter(teacher=user)  
        return Subject.objects.none() 
    
class SubjectStudentViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = SubjectStudent.objects.all()
    serializer_class = SubjectStudentSerializer

    @action(detail=True, methods=['get'], url_path='student-count')
    def student_count(self, request, pk=None):
       
        student_count = SubjectStudent.objects.filter(subject_id=pk).count()
        return Response({
            'subject_id': pk,
            'student_count': student_count
        })
# class SubjectDateViewSet(viewsets.ModelViewSet):
#     queryset = SubjectDate.objects.all()
#     serializer_class = SubjectDateSerializer
#     #permission_classes = [IsAuthenticated]

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         subject_date = serializer.save()
#         enrolled_students = SubjectStudent.objects.filter(subject=subject_date.subject)
#         attendance_list = []
#         for enrollment in enrolled_students:
#             attendance = StudentAttendance(
#                 student=enrollment.student,
#                 subject_date=subject_date,
#                 status=False
#             )
#             attendance_list.append(attendance)

#         StudentAttendance.objects.bulk_create(attendance_list)

#         return Response(serializer.data, status=status.HTTP_201_CREATED)
# class StudentAttendanceByDateViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = StudentAttendance.objects.all()
#     serializer_class = StudentAttendanceSerializer
#     #permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         user = self.request.user
#         subject_date_id = self.request.query_params.get('subject_date_id')

#         if user.role == 'teacher':
#             subjects = Subject.objects.filter(teacher=user)
#             queryset = queryset.filter(subject_date__subject__in=subjects)

#         if subject_date_id:
#             queryset = queryset.filter(subject_date__id=subject_date_id)

#         return queryset