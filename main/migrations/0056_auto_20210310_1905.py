# Generated by Django 3.0.7 on 2021-03-10 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0055_auto_20210310_1653'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='spentIndex',
        ),
        migrations.AddField(
            model_name='transaction',
            name='spent_index',
            field=models.IntegerField(db_index=True, default=0),
        ),
    ]