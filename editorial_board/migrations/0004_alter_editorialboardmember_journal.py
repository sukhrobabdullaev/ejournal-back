import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('editorial_board', '0003_backfill_journal'),
        ('journals', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='editorialboardmember',
            name='journal',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='board_members', to='journals.journal'),
            preserve_default=False,
        ),
    ]
