from django.db import models
from django.contrib.auth.models import User

ROLE_PERSONNEL = "personnel"
ROLE_ADMIN = "admin"

class Profile(models.Model):

    ROLE_PERSONNEL = ROLE_PERSONNEL
    ROLE_ADMIN = ROLE_ADMIN

    ROLE_CHOICES = [
        (ROLE_PERSONNEL ,"personnel"),                          
        (ROLE_ADMIN ,"admin"),
    ]

    user = models.OneToOneField( 
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_PERSONNEL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
       return f"{self.user.username} ({self.role})" 

    @property
    def is_admin(self):
        return self.role == Profile.ROLE_ADMIN

