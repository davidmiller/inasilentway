# Generated by Django 2.1.4 on 2018-12-10 10:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inasilentway', '0002_auto_20181210_1003'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='track',
            name='discogs_id',
        ),
    ]