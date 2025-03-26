from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction, connection
from picking.models import PickingList
from delivery.models import DeliveryOrder, LogisticsApprovalRequest
from packing.models import PackingList, PackingCost
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

@receiver(post_save, sender=PickingList)
def create_packing_data(sender, instance, **kwargs):
    """
    When a PickingList is marked as 'Completed', 
    automatically create associated PackingCost and PackingList
    and update total_items_packed for internal deliveries only
    """
    if instance.picked_status == 'Completed':
        try:
            with transaction.atomic():
                # Use direct SQL to insert PackingCost and get the ID
                with connection.cursor() as cursor:
                    # Generate a unique packing_cost_id
                    cursor.execute("""
                        INSERT INTO packing_cost 
                        (material_cost, labor_cost, total_packing_cost)
                        VALUES (0.00, 0.00, 0.00)
                        RETURNING packing_cost_id
                    """)
                    packing_cost_id = cursor.fetchone()[0]

                    # Create PackingList using the generated packing_cost_id
                    cursor.execute("""
                        INSERT INTO packing_list 
                        (packed_by, packing_status, packing_type, picking_list_id, packing_cost_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING packing_list_id
                    """, [
                        instance.picked_by, 
                        'Pending', 
                        None, 
                        instance.picking_list_id, 
                        packing_cost_id
                    ])
                    packing_list_id = cursor.fetchone()[0]
                
                    # Calculate and update total_items_packed if we have a delivery order
                    if instance.approval_request and instance.approval_request.del_order:
                        delivery_order = instance.approval_request.del_order
                        total_items = 0
                        
                        # Handle stock transfers (internal)
                        if delivery_order.stock_transfer_id:
                            print(f"Processing stock transfer: {delivery_order.stock_transfer_id}")
                            cursor.execute("""
                                SELECT quantity
                                FROM inventory.warehouse_movement
                                WHERE movement_id = %s
                            """, [delivery_order.stock_transfer_id])
                            result = cursor.fetchone()
                            print(f"Stock transfer query result: {result}")
                            if result and result[0]:
                                total_items = result[0]
                                print(f"Stock transfer items: {total_items}")
                            else:
                                print("No stock transfer quantity found")
                        
                        # Handle content items (internal)
                        elif delivery_order.content_id:
                            print(f"Processing content ID: {delivery_order.content_id}")
                            cursor.execute("""
                                SELECT quantity
                                FROM operations.document_items
                                WHERE content_id = %s
                            """, [delivery_order.content_id])
                            result = cursor.fetchone()
                            print(f"Content ID query result: {result}")
                            if result and result[0]:
                                total_items = result[0]
                                print(f"Content items: {total_items}")
                            else:
                                print("No content quantity found")
                        
                        # Update packing list with total items only if we found a quantity
                        if total_items > 0:
                            cursor.execute("""
                                UPDATE packing_list
                                SET total_items_packed = %s
                                WHERE packing_list_id = %s
                            """, [total_items, packing_list_id])
                            print(f"Updated total_items_packed to {total_items}")
                        else:
                            print(f"No items to pack found for delivery order {delivery_order.del_order_id}")
                
                print(f"Created PackingCost and PackingList for PickingList {instance.picking_list_id}")
        
        except Exception as e:
            print(f"Detailed Error creating packing data: {str(e)}")
            traceback.print_exc()