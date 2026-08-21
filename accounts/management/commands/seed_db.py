"""Seed database with superuser, topic areas, and optional sample users."""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from journals.models import MEMBERSHIP_STATUS_APPROVED, Journal, JournalMembership
from submissions.models import TopicArea

DEFAULT_JOURNAL_SLUG = "ditech-asia"


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
            journal = self._seed_default_journal()
            self._seed_topic_areas(journal)

            if not options["no_superuser"]:
                self._seed_superuser()

            if options["sample_users"]:
                self._seed_sample_users(journal)

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    def _seed_default_journal(self):
        journal, _ = Journal.objects.get_or_create(
            slug=DEFAULT_JOURNAL_SLUG,
            defaults=dict(
                name="Ditech Asia",
                doi_prefix="10.5555",
                from_name="Ditech Asia",
                is_active=True,
            ),
        )
        return journal

    def _seed_topic_areas(self, journal):
        areas = [
            ("Artificial Intelligence", "ai"),
            ("Software Engineering", "swe"),
            ("Machine Learning", "ml"),
            ("Data Science", "data-science"),
            ("Computer Vision", "cv"),
        ]
        created = 0
        for name, slug in areas:
            _, created_this = TopicArea.objects.get_or_create(
                journal=journal, slug=slug, defaults={"name": name}
            )
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

    def _seed_sample_users(self, journal):
        users_data = [
            ("author@test.com", "author123", "Sample Author", ["author"]),
            ("reviewer@test.com", "reviewer123", "Sample Reviewer", ["reviewer"]),
            ("editor@test.com", "editor123", "Sample Editor", ["editor"]),
        ]
        for email, password, name, roles in users_data:
            if User.objects.filter(email=email).exists():
                continue
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=name,
            )
            user.is_email_verified = True
            user.save()
            for role in roles:
                JournalMembership.objects.create(
                    user=user, journal=journal, role=role, status=MEMBERSHIP_STATUS_APPROVED
                )
            self.stdout.write(f"  User: {email}")
        self.stdout.write("  Sample users created (passwords: author123, reviewer123, editor123)")
