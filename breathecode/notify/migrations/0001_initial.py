# Generated by Django 3.1.2 on 2020-11-05 05:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('admissions', '0011_auto_20201006_0058'),
        ('authenticate', '0010_auto_20201105_0531'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SlackTeam',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slack_id', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=100)),
                ('sync_status',
                 models.CharField(choices=[('INCOMPLETED', 'Incompleted'), ('COMPLETED', 'Completed')],
                                  default='INCOMPLETED',
                                  help_text='Automatically set when synqued from slack',
                                  max_length=15)),
                ('sync_message',
                 models.CharField(blank=True,
                                  default=None,
                                  help_text='Contains any success or error messages depending on the status',
                                  max_length=100,
                                  null=True)),
                ('synqued_at', models.DateTimeField(blank=True, default=None, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('academy',
                 models.OneToOneField(blank=True, on_delete=django.db.models.deletion.CASCADE,
                                      to='admissions.academy')),
                ('credentials',
                 models.OneToOneField(blank=True,
                                      on_delete=django.db.models.deletion.CASCADE,
                                      to='authenticate.credentialsslack')),
                ('owner',
                 models.OneToOneField(blank=True,
                                      on_delete=django.db.models.deletion.CASCADE,
                                      to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SlackUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slack_id', models.CharField(max_length=50)),
                ('status_text', models.CharField(blank=True, max_length=255, null=True)),
                ('status_emoji', models.CharField(blank=True, max_length=100, null=True)),
                ('real_name', models.CharField(blank=True, max_length=100, null=True)),
                ('display_name', models.CharField(blank=True, max_length=100, null=True)),
                ('email', models.CharField(blank=True, max_length=100, null=True)),
                ('sync_status',
                 models.CharField(choices=[('INCOMPLETED', 'Incompleted'), ('COMPLETED', 'Completed')],
                                  default='INCOMPLETED',
                                  max_length=15)),
                ('sync_message',
                 models.CharField(blank=True,
                                  default=None,
                                  help_text='Contains any success or error messages depending on the status',
                                  max_length=100,
                                  null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notify.slackteam')),
                ('user',
                 models.ForeignKey(blank=True,
                                   null=True,
                                   on_delete=django.db.models.deletion.CASCADE,
                                   to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SlackChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slack_id', models.CharField(max_length=50)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('topic', models.CharField(blank=True, max_length=255, null=True)),
                ('purpose', models.CharField(blank=True, max_length=100, null=True)),
                ('sync_status',
                 models.CharField(choices=[('INCOMPLETED', 'Incompleted'), ('COMPLETED', 'Completed')],
                                  default='INCOMPLETED',
                                  max_length=15)),
                ('sync_message',
                 models.CharField(blank=True,
                                  default=None,
                                  help_text='Contains any success or error messages depending on the status',
                                  max_length=100,
                                  null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cohort',
                 models.ForeignKey(blank=True,
                                   null=True,
                                   on_delete=django.db.models.deletion.CASCADE,
                                   to=settings.AUTH_USER_MODEL)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notify.slackteam')),
            ],
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration_id', models.TextField(unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user',
                 models.ForeignKey(blank=True,
                                   null=True,
                                   on_delete=django.db.models.deletion.CASCADE,
                                   to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
