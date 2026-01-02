"""
Models for CSGO.NET case data caching system
"""

from django.db import models


class Case(models.Model):
    """
    Represents a case from CSGO.NET
    Data is stored here only when changes are detected.
    """
    # Risk level choices for volatility classification
    RISK_LOW = 'low'
    RISK_MEDIUM = 'medium'
    RISK_HIGH = 'high'
    RISK_CHOICES = [
        (RISK_LOW, 'Low Risk'),
        (RISK_MEDIUM, 'Medium Risk'),
        (RISK_HIGH, 'High Risk'),
    ]
    
    case_id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    image_url = models.URLField(max_length=500, blank=True)
    price_rub = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    price_eur = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    is_mining_case = models.BooleanField(default=False)
    expected_return = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    # Volatility metrics for high risk/high reward classification
    volatility = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, 
                                     help_text="Coefficient of variation - higher = more volatile")
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, null=True, blank=True,
                                  help_text="Categorized risk level: low, medium, high")
    max_multiplier = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text="Highest possible return multiplier (best item / case price)")
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'csgonet_case'
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.name} ({self.case_id})"


class CaseItem(models.Model):
    """
    Represents an item that can drop from a case.
    Stores probability (as percentage 0-100) and pricing information.
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='items')
    item_id = models.CharField(max_length=200)
    name = models.CharField(max_length=300)
    probability = models.DecimalField(max_digits=10, decimal_places=6)  # Percentage (0-100)
    price_rub = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    price_eur = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'csgonet_case_item'
        ordering = ['-probability']

    def __str__(self):
        return f"{self.name} - {self.probability:.4f}%"


class CaseHistory(models.Model):
    """
    Tracks when case data changes for historical analysis.
    Only created when a change is detected.
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='history')
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField()
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'csgonet_case_history'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['case', 'changed_at']),
            models.Index(fields=['field_changed']),
        ]

    def __str__(self):
        return f"{self.case.name}: {self.field_changed} changed at {self.changed_at}"
