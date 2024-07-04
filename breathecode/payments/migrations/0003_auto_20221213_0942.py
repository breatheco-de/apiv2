# Generated by Django 3.2.16 on 2022-12-13 09:42

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0048_academy_main_currency"),
        ("mentorship", "0017_auto_20221130_0504"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("payments", "0002_consumable_event_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancingOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monthly_price", models.IntegerField(default=1)),
                ("how_many_months", models.IntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name="PaymentServiceScheduler",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cohort_pattern", models.CharField(blank=True, default=None, max_length=80, null=True)),
                ("renew_every", models.IntegerField(default=1)),
                (
                    "renew_every_unit",
                    models.CharField(
                        choices=[("DAY", "Day"), ("WEEK", "Week"), ("MONTH", "Month"), ("YEAR", "Year")],
                        default="MONTH",
                        max_length=10,
                    ),
                ),
                ("academy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
                ("cohorts", models.ManyToManyField(blank=True, to="admissions.Cohort")),
                ("mentorship_services", models.ManyToManyField(blank=True, to="mentorship.MentorshipService")),
            ],
        ),
        migrations.CreateModel(
            name="PlanFinancing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("FREE_TRIAL", "Free trial"),
                            ("ACTIVE", "Active"),
                            ("CANCELLED", "Cancelled"),
                            ("DEPRECATED", "Deprecated"),
                            ("PAYMENT_ISSUE", "Payment issue"),
                            ("ERROR", "Error"),
                        ],
                        default="ACTIVE",
                        max_length=13,
                    ),
                ),
                ("status_message", models.CharField(blank=True, default=None, max_length=150, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("paid_at", models.DateTimeField()),
                ("pay_until", models.DateTimeField()),
                ("academy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
                ("invoices", models.ManyToManyField(blank=True, to="payments.Invoice")),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PlanServiceItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ],
        ),
        migrations.CreateModel(
            name="SubscriptionServiceItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "service_item",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="payments.serviceitem"),
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="servicestockscheduler",
            name="is_belongs_to_plan",
        ),
        migrations.RemoveField(
            model_name="servicestockscheduler",
            name="service_item",
        ),
        migrations.RemoveField(
            model_name="servicestockscheduler",
            name="subscription",
        ),
        migrations.AddField(
            model_name="plan",
            name="is_onboarding",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="bag",
            name="plans",
            field=models.ManyToManyField(blank=True, to="payments.Plan"),
        ),
        migrations.AlterField(
            model_name="bag",
            name="service_items",
            field=models.ManyToManyField(blank=True, to="payments.ServiceItem"),
        ),
        migrations.AlterField(
            model_name="currency",
            name="countries",
            field=models.ManyToManyField(
                blank=True,
                help_text="Countries that use this currency officially",
                related_name="currencies",
                to="admissions.Country",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="groups",
            field=models.ManyToManyField(blank=True, to="auth.Group"),
        ),
        migrations.AlterField(
            model_name="servicestockscheduler",
            name="consumables",
            field=models.ManyToManyField(blank=True, to="payments.Consumable"),
        ),
        migrations.AlterField(
            model_name="servicestockscheduler",
            name="last_renew",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="invoices",
            field=models.ManyToManyField(blank=True, to="payments.Invoice"),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="plans",
            field=models.ManyToManyField(blank=True, to="payments.Plan"),
        ),
        migrations.DeleteModel(
            name="Fixture",
        ),
        migrations.AddField(
            model_name="subscriptionserviceitem",
            name="subscription",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="payments.subscription"),
        ),
        migrations.AddField(
            model_name="planserviceitem",
            name="plan",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="payments.plan"),
        ),
        migrations.AddField(
            model_name="planserviceitem",
            name="plan_financing",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="payments.planfinancing",
            ),
        ),
        migrations.AddField(
            model_name="planserviceitem",
            name="service_item",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="payments.serviceitem"),
        ),
        migrations.AddField(
            model_name="planserviceitem",
            name="subscription",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="payments.subscription",
            ),
        ),
        migrations.AddField(
            model_name="planfinancing",
            name="plans",
            field=models.ManyToManyField(blank=True, to="payments.Plan"),
        ),
        migrations.AddField(
            model_name="planfinancing",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="paymentservicescheduler",
            name="service",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="payments.service"),
        ),
        migrations.AddField(
            model_name="financingoption",
            name="currency",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="payments.currency"),
        ),
        migrations.AddField(
            model_name="plan",
            name="financing_options",
            field=models.ManyToManyField(blank=True, to="payments.FinancingOption"),
        ),
        migrations.AddField(
            model_name="servicestockscheduler",
            name="plan_handler",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="payments.planserviceitem",
            ),
        ),
        migrations.AddField(
            model_name="servicestockscheduler",
            name="subscription_handler",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="payments.subscriptionserviceitem",
            ),
        ),
        migrations.RemoveField(
            model_name="plan",
            name="service_items",
            field=models.ManyToManyField(blank=True, through="payments.PlanServiceItem", to="payments.ServiceItem"),
        ),
        migrations.AddField(
            model_name="plan",
            name="service_items",
            field=models.ManyToManyField(blank=True, through="payments.PlanServiceItem", to="payments.ServiceItem"),
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="service_items",
            field=models.ManyToManyField(
                blank=True, through="payments.SubscriptionServiceItem", to="payments.ServiceItem"
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="service_items",
            field=models.ManyToManyField(
                blank=True, through="payments.SubscriptionServiceItem", to="payments.ServiceItem"
            ),
        ),
    ]
