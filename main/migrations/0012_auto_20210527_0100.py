# Generated by Django 3.0.14 on 2021-05-27 01:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_auto_20210526_0625'),
    ]

    operations = [
        migrations.AlterField(
            model_name='token',
            name='nft_token_group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='main.Token'),
        ),
    ]