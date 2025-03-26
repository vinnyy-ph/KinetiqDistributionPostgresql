from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction, connection
from picking.models import PickingList
from delivery.models import DeliveryOrder, LogisticsApprovalRequest
import traceback

@receiver(post_save, sender=PickingList)
def set_warehouse_for_picking_list(sender, instance, created, **kwargs):
    if created and instance.approval_request and instance.approval_request.del_order:
        try:
            delivery_order = instance.approval_request.del_order
            
            print(f"Delivery Order Details:")
            print(f"Content ID: {delivery_order.content_id}")
            print(f"Stock Transfer ID: {delivery_order.stock_transfer_id}")
            
            if delivery_order.content_id:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT warehouse_id 
                        FROM operations.document_items 
                        WHERE content_id = %s
                    """, [delivery_order.content_id])
                    result = cursor.fetchone()
                    
                    print(f"Warehouse ID from document_items: {result}")
                    
                    if result and result[0]:
                        PickingList.objects.filter(
                            picking_list_id=instance.picking_list_id
                        ).update(warehouse_id=result[0])
                        print(f"Updated warehouse_id to: {result[0]}")
            
            # Similar block for stock_transfer case
            elif delivery_order.stock_transfer_id:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT source 
                        FROM inventory.warehouse_movement 
                        WHERE movement_id = %s
                    """, [delivery_order.stock_transfer_id])
                    result = cursor.fetchone()
                    
                    print(f"Warehouse ID from warehouse_movement: {result}")
                    
                    if result and result[0]:
                        PickingList.objects.filter(
                            picking_list_id=instance.picking_list_id
                        ).update(warehouse_id=result[0])
                        print(f"Updated warehouse_id to: {result[0]}")
        
        except Exception as e:
            print(f"Detailed Error: {str(e)}")
            traceback.print_exc()