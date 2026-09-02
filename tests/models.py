from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)


class Supplier(models.Model):
    name = models.CharField(max_length=255)


class SupplierMetadata(models.Model):
    supplier = models.OneToOneField(Supplier, related_name="metadata", on_delete=models.CASCADE)
    properties = models.CharField(max_length=255)


class Partner(models.Model):
    name = models.CharField(max_length=255)


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, related_name="products", on_delete=models.CASCADE)
    backup_supplier = models.ForeignKey(
        Supplier, related_name="backup_products", on_delete=models.CASCADE, null=True, blank=True
    )
    partners = models.ManyToManyField(Partner, related_name="products", blank=True)
    # Non-relational copies of related pks, used to sideload without a Django relation.
    legacy_supplier_id = models.IntegerField(null=True, blank=True)
    partner_ids = models.JSONField(default=list, blank=True)


class ProductMetadata(models.Model):
    product = models.OneToOneField(Product, related_name="metadata", on_delete=models.CASCADE)
    properties = models.CharField(max_length=255)
