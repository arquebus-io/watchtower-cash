# Generated by Django 3.0.3 on 2020-03-02 04:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_auto_20200302_0416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='token',
            name='slpdb_api',
            field=models.TextField(blank=True),
        ),
    ]
