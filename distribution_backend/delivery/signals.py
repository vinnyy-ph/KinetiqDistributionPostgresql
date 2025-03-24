from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from .models import DeliveryOrder, LogisticsApprovalRequest  # Add LogisticsApprovalRequest here
from picking.models import PickingList
import uuid
import datetime  # Add this import


@receiver(pre_save, sender=DeliveryOrder)
def determine_delivery_type(sender, instance, **kwargs):
    # Logic to set del_type based on which fields are not null
    if instance.service_order_id or instance.sales_order_id:
        # If service_order_id or sales_order_id is not null, it's an external delivery
        instance.del_type = 'External Delivery'
    elif instance.production_request_id or instance.stock_transfer_id:
        # If production_request_id or stock_transfer_id is not null, it's an internal delivery
        instance.del_type = 'Internal Delivery'
    # If none of these fields are set, the delivery type remains unchanged

# Keep your existing post_save signal for creating picking lists
@receiver(post_save, sender=DeliveryOrder)
def create_picking_list_for_approved_orders(sender, instance, created, **kwargs):
    print(f"Signal triggered for {instance.del_order_id}, status: {instance.order_status}")
    
    # Only run this when the order status is 'Approved'
    if instance.order_status == 'Approved':
        print(f"Order {instance.del_order_id} has Approved status")
        
        # Check if a picking list already exists for this approval request
        if instance.approval_request:
            existing_picking = PickingList.objects.filter(approval_request=instance.approval_request).exists()
            print(f"Existing picking for this approval request: {existing_picking}")
            
            # Only create a new picking list if one doesn't already exist
            if not existing_picking:
                try:
                    # Generate a unique ID for the picking list
                    picking_id = f"DIS-PIL-{uuid.uuid4().hex[:6]}"
                    
                    # Create a new picking list entry using the valid enum value 'Not Started'
                    with transaction.atomic():
                        new_picking = PickingList.objects.create(
                            picking_list_id=picking_id,
                            picked_status='Not Started',  # Using the valid enum value
                            approval_request=instance.approval_request
                        )
                    print(f"Created new picking list {picking_id} for delivery order {instance.del_order_id}")
                except Exception as e:
                    print(f"Error creating picking list: {e}")
        else:
            print(f"Order {instance.del_order_id} has no approval request associated")


@receiver(post_save, sender=DeliveryOrder)
def create_logistics_approval_request(sender, instance, created, **kwargs):
    # Only run this when a new delivery order is created, not when updated
    if created:
        print(f"New DeliveryOrder created: {instance.del_order_id}")
        
        # Check if the delivery order already has an approval request
        if not instance.approval_request:
            try:
                # Generate a unique ID for the approval request
                approval_id = f"DIS-LOR-{uuid.uuid4().hex[:6]}"
                
                # Create a new approval request with default status (e.g., 'Pending')
                with transaction.atomic():
                    approval_request = LogisticsApprovalRequest.objects.create(
                        approval_request_id=approval_id,
                        request_date=datetime.date.today(),
                        approval_status='Pending',  # Use a valid enum value for your approval_status field
                        del_order=instance  # Link back to the delivery order
                    )
                    
                    # Update the delivery order to reference the new approval request
                    instance.approval_request = approval_request
                    # Use update() to avoid triggering this signal again
                    DeliveryOrder.objects.filter(pk=instance.pk).update(approval_request=approval_request)
                    
                print(f"Created new approval request {approval_id} for delivery order {instance.del_order_id}")
            except Exception as e:
                print(f"Error creating approval request: {e}")