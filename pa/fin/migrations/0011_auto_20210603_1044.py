# Generated by Django 3.1.8 on 2021-06-03 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fin', '0010_auto_20210603_1037'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stockexchange',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
