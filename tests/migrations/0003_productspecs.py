import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tests", "0002_alter_product_category_alter_product_partners_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductSpecs",
            fields=[
                (
                    "product",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="specs",
                        serialize=False,
                        to="tests.product",
                    ),
                ),
                ("color", models.CharField(max_length=255)),
            ],
        ),
    ]
