"""Call/contact and transcript models."""
from django.db import models
import uuid


class CollectionContact(models.Model):
    """Recorded collection contact event."""

    class Channel(models.TextChoices):
        PHONE = 'phone', 'Phone'
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        LETTER = 'letter', 'Letter'

    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='contacts')
    date = models.DateField()
    channel = models.CharField(max_length=20, choices=Channel.choices)
    outcome = models.CharField(max_length=100)
    agent = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='contacts_made'
    )
    source_system = models.CharField(max_length=100, default='collections')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collection_contact'
        ordering = ['-date']

    def __str__(self):
        return f"Contact {self.id}: {self.channel} - {self.outcome}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"contact-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class CallTranscript(models.Model):
    """Call transcript with extracted signals."""
    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='transcripts')
    language = models.CharField(max_length=10, default='en')
    text = models.TextField()
    signals = models.JSONField(default=list, help_text='Machine-extracted candidate signals')
    source_system = models.CharField(max_length=100, default='transcription-adapter')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'call_transcript'
        ordering = ['-created_at']

    def __str__(self):
        return f"Transcript {self.id}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"call-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class HardshipCase(models.Model):
    """Hardship tracking record."""

    class Status(models.TextChoices):
        REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review Required'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        APPROVED = 'APPROVED', 'Approved'
        DENIED = 'DENIED', 'Denied'

    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='hardship_cases')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REVIEW_REQUIRED)
    source = models.CharField(max_length=100, default='')
    specialist_required = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hardship_case'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"hardship-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class Dispute(models.Model):
    """Dispute tracking record."""

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        UNDER_INVESTIGATION = 'UNDER_INVESTIGATION', 'Under Investigation'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='disputes')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
    source = models.CharField(max_length=100, default='')
    collection_action_blocked = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dispute'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"dispute-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
