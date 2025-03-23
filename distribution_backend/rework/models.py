# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Rejection(models.Model):
    rejection_id = models.CharField(primary_key=True, max_length=255)
    rejection_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    rejection_reason = models.TextField()
    rejection_date = models.DateField(blank=True, null=True)
    delivery_receipt = models.ForeignKey('shipment.DeliveryReceipt', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rejection'


class ReworkOrder(models.Model):
    rework_id = models.CharField(primary_key=True, max_length=255)
    assigned_to = models.CharField(max_length=255, blank=True, null=True)
    rework_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    rework_date = models.DateField(blank=True, null=True)
    expected_completion = models.DateTimeField(blank=True, null=True)
    rejection = models.ForeignKey(Rejection, models.DO_NOTHING, blank=True, null=True)
    failed_shipment = models.ForeignKey('shipment.FailedShipment', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rework_order'
