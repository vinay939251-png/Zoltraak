"""Policy document models with versioning and chunks for RAG."""
from django.db import models
import uuid


class PolicyDocument(models.Model):
    """Versioned policy document for RAG retrieval."""

    class Status(models.TextChoices):
        ACTIVE_DEMO = 'ACTIVE_DEMO', 'Active (Demo)'
        ACTIVE = 'ACTIVE', 'Active'
        SUPERSEDED_DEMO = 'SUPERSEDED_DEMO', 'Superseded (Demo)'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'
        DRAFT = 'DRAFT', 'Draft'

    id = models.CharField(max_length=50, primary_key=True, default='')
    version = models.CharField(max_length=20)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    effective_date = models.DateField()
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    access_classification = models.CharField(max_length=30, default='internal')
    approved_by = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_policies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'policy_document'
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} v{self.version} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"POL-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class PolicyChunk(models.Model):
    """Traceable chunk of a policy document for RAG retrieval."""
    id = models.CharField(max_length=100, primary_key=True, default='')
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='chunks')
    text = models.TextField()
    topic = models.CharField(max_length=100)
    chunk_index = models.IntegerField(default=0)
    embedding = models.JSONField(null=True, blank=True, help_text='Vector embedding (pgvector substitute)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policy_chunk'
        ordering = ['chunk_index']

    def __str__(self):
        return f"{self.id}: {self.topic}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"{self.policy_id}#chunk-{self.chunk_index:02d}"
        super().save(*args, **kwargs)
