from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Market",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True)),
                ("slug", models.SlugField(max_length=220, unique=True)),
                ("category", models.CharField(max_length=80)),
                ("current_value", models.PositiveIntegerField()),
                ("trend_percent", models.DecimalField(decimal_places=1, max_digits=5)),
                ("trend_direction", models.CharField(choices=[("up", "Up"), ("down", "Down")], max_length=4)),
            ],
            options={"ordering": ("name",)},
        ),
    ]
