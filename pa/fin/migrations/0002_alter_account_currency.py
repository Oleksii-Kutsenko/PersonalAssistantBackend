# Generated by Django 3.2.5 on 2021-08-03 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fin', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='currency',
            field=models.CharField(choices=[('CAD', 'Canadian Dollar'), ('CHF', 'Swiss franc'), ('EUR', 'Euro'), ('GBP', 'Pound sterling'), ('UAH', 'Ukrainian Hryvnia'), ('USD', 'United States Dollar')], max_length=3),
        ),
    ]
