import hashlib
from django.db import models

class TranslationCache(models.Model):
    """
    High-performance persistent cache for translated texts.
    Reduces external network latency from ~300ms to <5ms for repetitive queries.
    """
    cache_key = models.CharField(max_length=64, primary_key=True, help_text="SHA-256 of lang pair + source text")
    source_text = models.TextField()
    translated_text = models.TextField()
    source_lang = models.CharField(max_length=12, default='auto')
    target_lang = models.CharField(max_length=12, default='bn')
    hit_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Translation Cache'
        verbose_name_plural = 'Translation Caches'
        indexes = [
            models.Index(fields=['source_lang', 'target_lang']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.source_lang}->{self.target_lang}] {self.source_text[:30]} -> {self.translated_text[:30]}"

    @classmethod
    def generate_cache_key(cls, source_text: str, source_lang: str, target_lang: str) -> str:
        normalized = f"{source_lang.strip().lower()}:::{target_lang.strip().lower()}:::{source_text.strip()}"
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
