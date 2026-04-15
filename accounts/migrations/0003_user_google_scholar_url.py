from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_groups_alter_user_is_superuser_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="google_scholar_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
