from django.db import models

class UserProfile(models.Model):
    user_id = models.IntegerField(unique=True)
    username = models.CharField(max_length=150)
    email = models.EmailField()
    role = models.CharField(max_length=10, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class DetectionHistory(models.Model):
    RESULT_CHOICES = [
        ('real', 'Real'),
        ('fake', 'Fake'),
    ]
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='detections'
    )
    image_name = models.CharField(max_length=255)
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    confidence = models.FloatField()
    label = models.CharField(max_length=512, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_profile.username} - {self.result} - {self.confidence}"