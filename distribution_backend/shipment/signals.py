from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction, connection
from shipment.models import ShipmentDetails, FailedShipment, DeliveryReceipt
import traceback
from datetime import date

@receiver(post_save, sender=ShipmentDetails)
def handle_shipment_status_change(sender, instance, **kwargs):
    """
    When a ShipmentDetails status is 'Failed', create a FailedShipment record if one doesn't exist.
    When a ShipmentDetails status is 'Shipped', create a DeliveryReceipt record if one doesn't exist.
    """
    try:
        # Get the current status
        current_status = instance.shipment_status
        
        # If status is 'Failed', check if FailedShipment already exists
        if current_status == 'Failed':
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT failed_shipment_id
                    FROM distribution.failed_shipment
                    WHERE shipment_id = %s
                """, [instance.shipment_id])
                result = cursor.fetchone()
                
                # If no FailedShipment exists, create one
                if not result:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO distribution.failed_shipment
                                (failure_date, failure_reason, resolution_status, shipment_id)
                                VALUES (%s, %s, %s, %s)
                                RETURNING failed_shipment_id
                            """, [
                                date.today(),
                                '',  # Empty failure_reason as requested (cannot be NULL)
                                'Pending',  # Default resolution_status
                                instance.shipment_id
                            ])
                            result = cursor.fetchone()
                            failed_shipment_id = result[0] if result else None
                            print(f"Created FailedShipment {failed_shipment_id} for shipment {instance.shipment_id}")
        
        # If status is 'Shipped', check if DeliveryReceipt already exists
        if current_status == 'Shipped':
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT delivery_receipt_id
                    FROM distribution.delivery_receipt
                    WHERE shipment_id = %s
                """, [instance.shipment_id])
                result = cursor.fetchone()
                
                # If no DeliveryReceipt exists, create one
                if not result:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO distribution.delivery_receipt
                                (delivery_date, received_by, signature, receipt_status, shipment_id)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING delivery_receipt_id
                            """, [
                                date.today(),
                                None,  # received_by will be filled later
                                '',  # Empty signature as requested (cannot be NULL)
                                'Pending',  # Default receipt_status
                                instance.shipment_id
                            ])
                            result = cursor.fetchone()
                            delivery_receipt_id = result[0] if result else None
                            print(f"Created DeliveryReceipt {delivery_receipt_id} for shipment {instance.shipment_id}")
    except Exception as e:
        print(f"Error handling shipment status change: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=FailedShipment)
def handle_failed_shipment_update(sender, instance, **kwargs):
    """
    When a FailedShipment's failure_reason is updated from empty to non-empty,
    create a ReworkOrder record linked to that FailedShipment.
    """
    try:
        # Check if failure_reason is not empty
        if instance.failure_reason and instance.failure_reason.strip():
            # First check if there's already a ReworkOrder for this FailedShipment
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT rework_id
                    FROM distribution.rework_order
                    WHERE failed_shipment_id = %s
                """, [instance.failed_shipment_id])
                result = cursor.fetchone()
                
                # If no ReworkOrder exists yet, create one
                if not result:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO distribution.rework_order
                                (assigned_to, rework_status, rework_date, expected_completion, failed_shipment_id, rework_types)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                RETURNING rework_id
                            """, [
                                None,  # assigned_to will be filled later
                                'Pending',  # Default rework_status
                                date.today(),  # rework_date is today
                                None,  # expected_completion will be set later
                                instance.failed_shipment_id,
                                'Failed Shipment'  # rework_types
                            ])
                            result = cursor.fetchone()
                            rework_id = result[0] if result else None
                            print(f"Created ReworkOrder {rework_id} for FailedShipment {instance.failed_shipment_id}")
    except Exception as e:
        print(f"Error handling failed shipment update: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=DeliveryReceipt)
def handle_delivery_receipt_update(sender, instance, **kwargs):
    """
    When a DeliveryReceipt's signature is updated from empty to non-empty:
    1. Create a BillingReceipt record
    2. For sales orders, link to the corresponding sales_invoice_id
    3. Create a GoodsIssue record linked to the BillingReceipt
    4. Update the original sales order with the new goods_issue_id
    """
    try:
        print(f"Processing delivery receipt {instance.delivery_receipt_id} with signature: '{instance.signature}'")
        
        # Check if signature is not empty
        if instance.signature and instance.signature.strip():
            # First check if there's already a BillingReceipt for this DeliveryReceipt
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT billing_receipt_id
                    FROM distribution.billing_receipt
                    WHERE delivery_receipt_id = %s
                """, [instance.delivery_receipt_id])
                result = cursor.fetchone()
                
                # If no BillingReceipt exists yet, create one
                if not result:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            # Get the total_amount from delivery_receipt
                            total_amount = instance.total_amount or 0
                            
                            # Trace back to find if this is a sales order delivery
                            sales_invoice_id = None
                            sales_order_id = None
                            
                            # Step 1: Get the shipment_id from delivery_receipt
                            if instance.shipment_id:
                                # Step 2: Get the packing_list_id from shipment
                                cursor.execute("""
                                    SELECT packing_list_id
                                    FROM distribution.shipment_details
                                    WHERE shipment_id = %s
                                """, [instance.shipment_id])
                                packing_result = cursor.fetchone()
                                
                                if packing_result and packing_result[0]:
                                    # Step 3: Get the picking_list_id from packing_list
                                    cursor.execute("""
                                        SELECT picking_list_id
                                        FROM distribution.packing_list
                                        WHERE packing_list_id = %s
                                    """, [packing_result[0]])
                                    picking_result = cursor.fetchone()
                                    
                                    if picking_result and picking_result[0]:
                                        # Step 4: Get the approval_request_id from picking_list
                                        cursor.execute("""
                                            SELECT approval_request_id
                                            FROM distribution.picking_list
                                            WHERE picking_list_id = %s
                                        """, [picking_result[0]])
                                        approval_result = cursor.fetchone()
                                        
                                        if approval_result and approval_result[0]:
                                            # Step 5: Get the delivery_order from approval_request
                                            cursor.execute("""
                                                SELECT del_order_id
                                                FROM distribution.logistics_approval_request
                                                WHERE approval_request_id = %s
                                            """, [approval_result[0]])
                                            delivery_result = cursor.fetchone()
                                            
                                            if delivery_result and delivery_result[0]:
                                                # Step 6: Check if this is a sales order delivery
                                                cursor.execute("""
                                                    SELECT sales_order_id
                                                    FROM distribution.delivery_order
                                                    WHERE del_order_id = %s
                                                """, [delivery_result[0]])
                                                order_result = cursor.fetchone()
                                                
                                                if order_result and order_result[0]:
                                                    # This is a sales order delivery!
                                                    sales_order_id = order_result[0]
                                                    
                                                    # Step 7: Find the corresponding sales invoice
                                                    cursor.execute("""
                                                        SELECT invoice_id
                                                        FROM sales.sales_invoices
                                                        WHERE order_id = %s
                                                    """, [sales_order_id])
                                                    invoice_result = cursor.fetchone()
                                                    
                                                    if invoice_result and invoice_result[0]:
                                                        sales_invoice_id = invoice_result[0]
                                                        print(f"Found sales_invoice_id {sales_invoice_id} for sales_order {sales_order_id}")
                            
                            # Create the billing receipt with or without the sales_invoice_id
                            if sales_invoice_id:
                                cursor.execute("""
                                    INSERT INTO distribution.billing_receipt
                                    (delivery_receipt_id, sales_invoice_id, total_receipt)
                                    VALUES (%s, %s, %s)
                                    RETURNING billing_receipt_id
                                """, [
                                    instance.delivery_receipt_id,
                                    sales_invoice_id,
                                    total_amount
                                ])
                            else:
                                cursor.execute("""
                                    INSERT INTO distribution.billing_receipt
                                    (delivery_receipt_id, total_receipt)
                                    VALUES (%s, %s)
                                    RETURNING billing_receipt_id
                                """, [
                                    instance.delivery_receipt_id,
                                    total_amount
                                ])
                            
                            result = cursor.fetchone()
                            billing_receipt_id = result[0] if result else None
                            print(f"Created BillingReceipt {billing_receipt_id} for DeliveryReceipt {instance.delivery_receipt_id}")
                            
                            if sales_invoice_id:
                                print(f"  - Linked to sales_invoice_id: {sales_invoice_id}")
                            
                            # Create a GoodsIssue record linked to the billing receipt
                            if billing_receipt_id:
                                # Try to get an employee_id (from picked_by or a default)
                                employee_id = None
                                
                                # Try to find the picker who handled this order
                                if packing_result and packing_result[0]:
                                    cursor.execute("""
                                        SELECT picked_by 
                                        FROM distribution.picking_list 
                                        WHERE picking_list_id = (
                                            SELECT picking_list_id 
                                            FROM distribution.packing_list 
                                            WHERE packing_list_id = %s
                                        )
                                    """, [packing_result[0]])
                                    picked_by_result = cursor.fetchone()
                                    if picked_by_result and picked_by_result[0]:
                                        employee_id = picked_by_result[0]
                                
                                cursor.execute("""
                                    INSERT INTO distribution.goods_issue
                                    (issue_date, issued_by, billing_receipt_id)
                                    VALUES (%s, %s, %s)
                                    RETURNING goods_issue_id
                                """, [
                                    date.today(),
                                    employee_id,
                                    billing_receipt_id
                                ])
                                goods_issue_result = cursor.fetchone()
                                goods_issue_id = goods_issue_result[0] if goods_issue_result else None
                                
                                if goods_issue_id:
                                    print(f"Created GoodsIssue {goods_issue_id} for BillingReceipt {billing_receipt_id}")
                                    
                                    # Update the sales order with the goods_issue_id if this is a sales order
                                    if sales_order_id:
                                        cursor.execute("""
                                            UPDATE sales.orders
                                            SET goods_issue_id = %s
                                            WHERE order_id = %s
                                        """, [goods_issue_id, sales_order_id])
                                        print(f"Updated sales.orders {sales_order_id} with goods_issue_id {goods_issue_id}")
    except Exception as e:
        print(f"Error handling delivery receipt update: {str(e)}")
        traceback.print_exc()