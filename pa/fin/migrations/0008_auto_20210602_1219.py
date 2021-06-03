# Generated by Django 3.1.8 on 2021-06-02 12:19

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fin', '0007_auto_20210602_0948'),
    ]

    operations = [
        migrations.CreateModel(
            name='StockExchange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('aliases', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), size=None)),
            ],
        ),
        migrations.AlterField(
            model_name='ticker',
            name='stock_exchange',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='fin.stockexchange'),
        ),
    ]
