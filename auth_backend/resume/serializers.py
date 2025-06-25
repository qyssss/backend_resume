from rest_framework import serializers

class PersonalSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    gender = serializers.CharField(max_length=10)
    age = serializers.CharField(max_length=10)
    degree = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    photo = serializers.CharField(allow_blank=True)

class SkillsSerializer(serializers.Serializer):
    proficient = serializers.ListField(child=serializers.CharField(max_length=50))
    familiar = serializers.ListField(child=serializers.CharField(max_length=50))

class EducationSerializer(serializers.Serializer):
    school = serializers.CharField(max_length=100)
    major = serializers.CharField(max_length=100)
    degree = serializers.CharField(max_length=50)
    score = serializers.CharField(max_length=50)

class ExperienceSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=100)
    company = serializers.CharField(max_length=100)
    period = serializers.CharField(max_length=50)
    content = serializers.CharField()
    result = serializers.CharField()

class HonorSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=100)
    date = serializers.CharField(max_length=50)
    description = serializers.CharField()

class ResumeSerializer(serializers.Serializer):
    personal = PersonalSerializer()
    skills = SkillsSerializer()
    education = EducationSerializer(many=True)
    experiences = ExperienceSerializer(many=True)
    honors = HonorSerializer(many=True)
    selfEvaluation = serializers.CharField()