import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0002_market"),
    ]

    operations = [
        migrations.AddField(
            model_name="market",
            name="trend_updated_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="market",
            name="expires_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="MarketPosition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency", models.CharField(choices=[("carrots", "carrots"), ("apples", "apples"), ("horseshoes", "horseshoes"), ("hay", "hay")], max_length=20)),
                ("amount", models.PositiveBigIntegerField()),
                ("market", models.ForeignKey(on_delete=models.CASCADE, to="landing.market")),
                ("user", models.ForeignKey(on_delete=models.CASCADE, to="auth.user")),
            ],
        ),
        migrations.AddConstraint(
            model_name="marketposition",
            constraint=models.UniqueConstraint(fields=("user", "market", "currency"), name="unique_market_position"),
        ),
    ]
