from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Token(models.Model):
    name = models.CharField(max_length=100)
    tokenid = models.CharField(max_length=200)
    target_address = models.CharField(max_length=500)
    confirmation_limit = models.IntegerField(default=0)
    slpdb_api = models.TextField(blank=True)

    def __str__(self):
        return self.name


class BlockHeight(models.Model):
    number = models.IntegerField(default=0, unique=True)
    transactions_count = models.IntegerField(default=0)
    created_datetime = models.DateTimeField(null=True, blank=True)
    updated_datetime = models.DateTimeField(null=True, blank=True)
    processed = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.created_datetime = timezone.now()
        if self.processed:
            self.updated_datetime = timezone.now()
        super(BlockHeight,self).save(*args, **kwargs)


class Transaction(models.Model):
    txid = models.CharField(max_length=200, unique=True)
    amount = models.FloatField(default=0)
    acknowledge = models.BooleanField(default=False)
    blockheight = models.ForeignKey(BlockHeight, on_delete=models.CASCADE, related_name='transactions', null=True)
    source = models.CharField(max_length=200, null=True)
    created_datetime = models.DateTimeField(default=timezone.now)
    token = models.ForeignKey(Token, on_delete=models.CASCADE)

    def __str__(self):
        return self.txid

class Subscriber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    token = models.ManyToManyField(Token, related_name='subscriber')

class SlpAddress(models.Model):
    address = models.CharField(max_length=200, unique=True)
    transactions = models.ManyToManyField(Transaction) 

    class Meta:
        verbose_name = 'Slp Address'
        verbose_name_plural = 'Slp Addresses'
        
    def __str__(self):
        return self.address