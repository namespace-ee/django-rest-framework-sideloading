from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)


class Supplier(models.Model):
    name = models.CharField(max_length=255)


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
