from django.db.models.signals import post_save
from django.dispatch import receiver
from delivery.models import LogisticsApprovalRequest, DeliveryOrder
from picking.models import PickingList
from django.db import transaction, connection
from django.utils import timezone

@receiver(post_save, sender=LogisticsApprovalRequest)
def handle_approval_request_update(sender, instance, **kwargs):
    """
    Signal handler to process approval request changes.
    When approval_status changes to 'Approved', update delivery order and create picking list.
    """
    # Only proceed if the approval status is 'Approved'
    if instance.approval_status == 'Approved':
        try:
            with transaction.atomic():
                # Set approval date to current date
                LogisticsApprovalRequest.objects.filter(
                    approval_request_id=instance.approval_request_id
                ).update(approval_date=timezone.now().date())
                
                # Update the associated delivery order status
                if instance.del_order:
                    # Verify at least one delivery type ID is not null
                    if instance.del_order.sales_order_id or instance.del_order.service_order_id or \
                       instance.del_order.stock_transfer_id or instance.del_order.content_id:
                        # Update order status to Approved
                        DeliveryOrder.objects.filter(del_order_id=instance.del_order.del_order_id).update(
                            order_status='Approved'
                        )
                        
                        # Determine warehouse_id
                        warehouse_id = None
                        if instance.del_order.content_id:
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    SELECT warehouse_id 
                                    FROM operations.document_items 
                                    WHERE content_id = %s
                                """, [instance.del_order.content_id])
                                result = cursor.fetchone()
                                warehouse_id = result[0] if result else None
                        
                        elif instance.del_order.stock_transfer_id:
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    SELECT source 
                                    FROM inventory.warehouse_movement 
                                    WHERE movement_id = %s
                                """, [instance.del_order.stock_transfer_id])
                                result = cursor.fetchone()
                                warehouse_id = result[0] if result else None
                        
                        # Create new picking list record
                        PickingList.objects.create(
                            picked_status='Not Started',
                            approval_request=instance,
                            warehouse_id=warehouse_id  # Add this line
                        )
                        print(f"Created new picking list for approval request {instance.approval_request_id}")
        except Exception as e:
            print(f"Error processing approval: {str(e)}")