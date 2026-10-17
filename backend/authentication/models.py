"""Custom User model with role-based access control."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model with collections-specific roles."""

    class Role(models.TextChoices):
        COLLECTIONS_AGENT = 'collections_agent', 'Collections Agent'
        TEAM_LEAD = 'team_lead', 'Team Lead'
        HARDSHIP_SPECIALIST = 'hardship_specialist', 'Hardship Specialist'
        DATA_STEWARD = 'data_steward', 'Data Steward'
        ADMINISTRATOR = 'administrator', 'Administrator'

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.COLLECTIONS_AGENT,
    )

    class Meta:
        db_table = 'auth_user'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_agent(self):
        return self.role == self.Role.COLLECTIONS_AGENT

    @property
    def is_lead(self):
        return self.role == self.Role.TEAM_LEAD

    @property
    def is_steward(self):
        return self.role == self.Role.DATA_STEWARD

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMINISTRATOR

    @property
    def is_hardship_specialist(self):
        return self.role == self.Role.HARDSHIP_SPECIALIST
