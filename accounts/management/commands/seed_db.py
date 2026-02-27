"""Seed database with superuser, topic areas, and optional sample users."""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import APPROVAL_APPROVED, User
from submissions.models import TopicArea


class Command(BaseCommand):
    help = "Seed database: superuser, topic areas, optional sample users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample-users",
            action="store_true",
            help="Create sample author, reviewer, editor users",
        )
        parser.add_argument(
            "--no-superuser",
            action="store_true",
            help="Skip superuser creation (e.g. if already exists)",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_topic_areas()

            if not options["no_superuser"]:
                self._seed_superuser()

            if options["sample_users"]:
                self._seed_sample_users()

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    def _seed_topic_areas(self):
        areas = [
            ("Artificial Intelligence", "ai"),
            ("Software Engineering", "swe"),
            ("Machine Learning", "ml"),
            ("Data Science", "data-science"),
            ("Computer Vision", "cv"),
        ]
        created = 0
        for name, slug in areas:
            _, created_this = TopicArea.objects.get_or_create(slug=slug, defaults={"name": name})
            if created_this:
                created += 1
        self.stdout.write(f"  Topic areas: {created} created")

    def _seed_superuser(self):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@ejournal.local")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123")
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"  Superuser {email} already exists")
            return
        User.objects.create_superuser(
            email=email,
            password=password,
            full_name="Admin",
        )
        self.stdout.write(f"  Superuser: {email} / {password}")

    def _seed_sample_users(self):
        users_data = [
            ("author@test.com", "author123", "Sample Author", ["author"]),
            ("reviewer@test.com", "reviewer123", "Sample Reviewer", ["reviewer"], APPROVAL_APPROVED, None),
            ("editor@test.com", "editor123", "Sample Editor", ["editor"], None, APPROVAL_APPROVED),
        ]
        for row in users_data:
            email, password, name, roles = row[0], row[1], row[2], row[3]
            reviewer_status = row[4] if len(row) > 4 else None
            editor_status = row[5] if len(row) > 5 else None
            if User.objects.filter(email=email).exists():
                continue
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=name,
                roles=roles,
            )
            if reviewer_status:
                user.reviewer_status = reviewer_status
            if editor_status:
                user.editor_status = editor_status
            user.save()
            self.stdout.write(f"  User: {email}")
        self.stdout.write("  Sample users created (passwords: author123, reviewer123, editor123)")
