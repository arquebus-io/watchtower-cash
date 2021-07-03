# Generated by Django 3.0.14 on 2021-06-21 09:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_auto_20210620_2218'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='wallet',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='main.Wallet'),
        ),
        migrations.AddField(
            model_name='wallet',
            name='wallet_type',
            field=models.CharField(db_index=True, default='bch', max_length=5),
            preserve_default=False,
        )
    ]