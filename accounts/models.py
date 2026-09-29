"""User models for traveller profiles and authorization roles."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TRAVELER = "traveler", "Traveler"
        AGENT = "agent", "Travel Agent"
        ADMIN = "admin", "Administrator"

    RoleChoices = Role

    email = models.EmailField(unique=True, help_text="Primary email used for account contact.")
    phone = models.CharField(max_length=20, blank=True, help_text="International phone number.")
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    travel_preferences = models.JSONField(
        default=dict, blank=True, help_text="Flexible preferences such as climate and activities."
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TRAVELER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email"]), models.Index(fields=["role"])]
        verbose_name = "traveller"
        verbose_name_plural = "travellers"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def full_name(self):
        return self.display_name
