# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class PackingCost(models.Model):
    packing_cost_id = models.CharField(primary_key=True, max_length=255)
    material_cost = models.DecimalField(max_digits=10, decimal_places=2)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_packing_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'packing_cost'


class PackingList(models.Model):
    packing_list_id = models.CharField(primary_key=True, max_length=255)
    packed_by = models.CharField(max_length=255, blank=True, null=True)
    packing_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    packing_type = models.TextField(blank=True, null=True)  # This field type is a guess.
    total_items_packed = models.IntegerField(blank=True, null=True)
    packing_cost = models.ForeignKey(PackingCost, models.DO_NOTHING, blank=True, null=True)
    picking_list = models.ForeignKey('PickingList', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'packing_list'
