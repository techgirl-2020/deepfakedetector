from django.contrib.auth.models import AbstractUser
from django.db import models

# We extend Django's built-in User model
# AbstractUser already has: username, email, password, is_active, date_joined
class CustomUser(AbstractUser):
    # We add one extra field: role
    ROLE_CHOICES = [
        ('user', 'User'),       # normal user
        ('admin', 'Admin'),     # admin user
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user'          # everyone is a normal user by default
    )

    def __str__(self):
        return self.username