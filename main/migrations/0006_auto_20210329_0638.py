# Generated by Django 3.0.7 on 2021-03-29 06:38

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_auto_20210326_1301'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='recipient',
            options={},
        ),
        migrations.RemoveField(
            model_name='recipient',
            name='slack_user_details',
        ),
        migrations.RemoveField(
            model_name='recipient',
            name='telegram_user_details',
        ),
        migrations.AddField(
            model_name='recipient',
            name='telegram_id',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='recipient',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='main.Recipient'),
        ),
    ]