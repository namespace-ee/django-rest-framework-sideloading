from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tests", "0002_alter_product_category_alter_product_partners_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="legacy_supplier_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="partner_ids",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
