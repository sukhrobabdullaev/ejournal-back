import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journals', '0001_initial'),
        ('submissions', '0008_backfill_journal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalissue',
            name='journal',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='issues', to='journals.journal'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='submission',
            name='journal',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='journals.journal'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='topicarea',
            name='journal',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='topic_areas', to='journals.journal'),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='journalissue',
            constraint=models.UniqueConstraint(fields=('journal', 'volume', 'issue_number', 'publication_year'), name='uniq_issue_journal_vol_no_year'),
        ),
        migrations.AddConstraint(
            model_name='topicarea',
            constraint=models.UniqueConstraint(fields=('journal', 'slug'), name='uniq_topicarea_journal_slug'),
        ),
    ]
