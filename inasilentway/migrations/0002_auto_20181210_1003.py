# Generated by Django 2.1.4 on 2018-12-10 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inasilentway', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='artist',
            name='discogs_id',
            field=models.CharField(default=None, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='label',
            name='discogs_id',
            field=models.CharField(default=None, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='record',
            name='discogs_id',
            field=models.CharField(default=None, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='track',
            name='discogs_id',
            field=models.CharField(default=None, max_length=200),
            preserve_default=False,
        ),
    ]
