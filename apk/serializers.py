from rest_framework import serializers

class JiraIssueSerializer(serializers.Serializer):
    comment = serializers.JSONField()
