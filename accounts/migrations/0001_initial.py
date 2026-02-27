"""Initial migration for accounts.User."""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("affiliation", models.CharField(blank=True, max_length=255)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("orcid_id", models.CharField(blank=True, max_length=50)),
                ("is_email_verified", models.BooleanField(default=False)),
                ("roles", models.JSONField(default=list)),
                ("reviewer_status", models.CharField(blank=True, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], max_length=20, null=True)),
                ("editor_status", models.CharField(blank=True, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], max_length=20, null=True)),
                ("why_to_be", models.TextField(blank=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("date_joined", models.DateTimeField(auto_now_add=True)),
                ("groups", models.ManyToManyField(blank=True, related_name="accounts_user_set", to="auth.group")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="accounts_user_set", to="auth.permission")),
            ],
            options={
                "db_table": "accounts_user",
            },
        ),
    ]
