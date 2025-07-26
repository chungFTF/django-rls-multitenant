from django.db import models
import uuid

class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BranchAwareModel(models.Model):
    branch_id = models.UUIDField(db_index=True)
    
    class Meta:
        abstract = True

class Sales(BranchAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = models.IntegerField(default=0)
    product_category = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['branch_id', 'date', 'product_category']
    
    def save(self, *args, **kwargs):
        if self.branch:
            self.branch_id = self.branch.id
        super().save(*args, **kwargs)