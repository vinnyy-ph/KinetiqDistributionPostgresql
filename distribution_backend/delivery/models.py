# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class DeliveryOrder(models.Model):
    del_order_id = models.CharField(primary_key=True, max_length=255)
    order_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    content_id = models.CharField(max_length=255, blank=True, null=True)
    is_project_based = models.TextField(blank=True, null=True)  # This field type is a guess.
    is_partial_delivery = models.TextField(blank=True, null=True)  # This field type is a guess.
    service_order_id = models.CharField(max_length=255, blank=True, null=True)
    production_request_id = models.CharField(max_length=255, blank=True, null=True)
    stock_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    sales_order_id = models.CharField(max_length=255, blank=True, null=True)
    approval_request = models.ForeignKey('delivery.LogisticsApprovalRequest', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'delivery_order'


class LogisticsApprovalRequest(models.Model):
    approval_request_id = models.CharField(primary_key=True, max_length=255)
    request_date = models.DateField(blank=True, null=True)
    approval_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    approval_date = models.DateField(blank=True, null=True)
    approved_by = models.CharField(max_length=255, blank=True, null=True)
    del_order = models.ForeignKey(DeliveryOrder, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'logistics_approval_request'
