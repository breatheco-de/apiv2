# Generated by Django 3.2.16 on 2022-12-26 23:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0047_merge_20220924_0611'),
        ('mentorship', '0017_auto_20221130_0504'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatBot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, default=None, null=True)),
                ('api_key', models.CharField(blank=True, max_length=250)),
                ('api_organization', models.CharField(blank=True, max_length=250)),
                ('academy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='admissions.academy')),
                ('syllabus', models.ManyToManyField(blank=True, to='admissions.Syllabus')),
            ],
        ),
    ]
