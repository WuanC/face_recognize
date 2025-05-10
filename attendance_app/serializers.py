from rest_framework import serializers
from .models import CustomUser, Subject, SubjectDate, StudentAttendance, SubjectStudent


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()   
    class Meta:
        model = Subject
        fields = '__all__'
    def get_teacher_name(self, obj):
        return f"{obj.teacher.first_name} {obj.teacher.last_name}" if obj.teacher else None    

# class SubjectStudentSerializer(serializers.ModelSerializer):
#     subject = SubjectSerializer()  
#     class Meta:
#         model = SubjectStudent
#         fields = '__all__'

class SubjectStudentSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all()) 
    subject_name = serializers.CharField(source='subject.name', read_only=True)  
    class Meta:
        model = SubjectStudent
        fields = ['id', 'subject', 'subject_name', 'student']  
class SubjectDateSerializer(serializers.ModelSerializer):
    name_subject = serializers.SerializerMethodField()  
    class Meta:
        model = SubjectDate
        fields = ['id', 'subject', 'current_date','name_subject','status']
    def get_name_subject(self, obj):
        return obj.subject.name if obj.subject else None  

class StudentAttendanceSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField()  
    subject_date = SubjectDateSerializer()  
    name_subject = serializers.SerializerMethodField()  
    
    class Meta:
        model = StudentAttendance
        fields = ['student', 'subject_date','name_subject','status']

    def get_name_subject(self, obj):
        return obj.subject_date.subject.name if obj.subject_date else None

