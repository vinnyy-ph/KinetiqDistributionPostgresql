from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction, connection
from shipment.models import ShipmentDetails, FailedShipment, DeliveryReceipt
from rework.models import Rejection
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
        # Debug output
        print(f"Processing failed shipment: {instance.failed_shipment_id}")
        print(f"Failure reason: '{instance.failure_reason}'")
        
        # Check if failure_reason is not empty
        if instance.failure_reason and instance.failure_reason.strip():
            print(f"Failure reason is not empty, checking for existing ReworkOrder")
            
            # First check if there's already a ReworkOrder for this FailedShipment
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT rework_id
                    FROM distribution.rework_order
                    WHERE failed_shipment_id = %s
                """, [instance.failed_shipment_id])
                result = cursor.fetchone()
                
                if result:
                    print(f"Found existing ReworkOrder: {result[0]}")
                else:
                    print("No existing ReworkOrder found, creating new one")
                
                # If no ReworkOrder exists yet, create one
                if not result:
                    try:
                        with transaction.atomic():
                            cursor.execute("""
                                INSERT INTO distribution.rework_order
                                (assigned_to, rework_status, rework_date, expected_completion, failed_shipment_id, rejection_id, rework_types)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                RETURNING rework_id
                            """, [
                                None,  # assigned_to will be filled later
                                'Pending',  # Default rework_status
                                date.today(),  # rework_date is today
                                None,  # expected_completion will be set later
                                instance.failed_shipment_id,
                                None,  # rejection_id is NULL as this is from a failed shipment
                                'Failed Shipment'  # rework_types
                            ])
                            result = cursor.fetchone()
                            rework_id = result[0] if result else None
                            print(f"Created ReworkOrder {rework_id} for FailedShipment {instance.failed_shipment_id}")
                            
                            # Check if this is from a sales order and update the sales order with rework_id
                            if rework_id:
                                try:
                                    # Trace back to find if this is a sales order delivery
                                    # Note: Changed 'do' alias to 'delivery' to avoid SQL reserved keyword issue
                                    cursor.execute("""
                                        SELECT delivery.sales_order_id
                                        FROM distribution.failed_shipment fs
                                        JOIN distribution.shipment_details sd ON fs.shipment_id = sd.shipment_id
                                        JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                                        JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                                        JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                                        JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                                        WHERE fs.failed_shipment_id = %s AND delivery.sales_order_id IS NOT NULL
                                    """, [instance.failed_shipment_id])
                                    
                                    order_result = cursor.fetchone()
                                    if order_result and order_result[0]:
                                        sales_order_id = order_result[0]
                                        # Update the sales order with the rework_id
                                        cursor.execute("""
                                            UPDATE sales.orders
                                            SET rework_id = %s, goods_issue_id = NULL
                                            WHERE order_id = %s
                                        """, [rework_id, sales_order_id])
                                        print(f"Updated sales.orders {sales_order_id} with rework_id {rework_id}")
                                except Exception as inner_e:
                                    print(f"Error updating sales order with rework_id: {str(inner_e)}")
                                    traceback.print_exc()
                    except Exception as e:
                        print(f"Error creating ReworkOrder: {str(e)}")
                        traceback.print_exc()
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
        print(f"Processing delivery receipt {instance.delivery_receipt_id} with signature: '{instance.signature}' and status: '{instance.receipt_status}'")
        
        # Check if signature is not empty AND receipt_status is not 'Rejected'
        if instance.signature and instance.signature.strip() and instance.receipt_status != 'Rejected':
            # Update receipt_status to "Received" if not already
            if instance.receipt_status != 'Received':
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE distribution.delivery_receipt
                        SET receipt_status = 'Received'
                        WHERE delivery_receipt_id = %s
                    """, [instance.delivery_receipt_id])
                    print(f"Updated delivery receipt {instance.delivery_receipt_id} status to 'Received'")
            
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
                            
                            # Trace back to find if this is a sales order delivery or service order
                            sales_invoice_id = None
                            service_billing_id = None
                            sales_order_id = None
                            delivery_type = None
                            
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
                                                # Step 6: Get delivery order details to determine type
                                                cursor.execute("""
                                                    SELECT sales_order_id, service_order_id, content_id, stock_transfer_id, del_type
                                                    FROM distribution.delivery_order
                                                    WHERE del_order_id = %s
                                                """, [delivery_result[0]])
                                                order_result = cursor.fetchone()
                                                
                                                if order_result:
                                                    sales_order_id = order_result[0]
                                                    service_order_id = order_result[1]
                                                    content_id = order_result[2]
                                                    stock_transfer_id = order_result[3]
                                                    delivery_type = order_result[4]
                                                    
                                                    print(f"Delivery type: {delivery_type}")
                                                    print(f"Sales order ID: {sales_order_id}")
                                                    print(f"Service order ID: {service_order_id}")
                                                    print(f"Content ID: {content_id}")
                                                    print(f"Stock transfer ID: {stock_transfer_id}")
                                                    
                                                    # Handle sales order type
                                                    if sales_order_id:
                                                        # Find corresponding sales invoice
                                                        cursor.execute("""
                                                            SELECT invoice_id
                                                            FROM sales.sales_invoices
                                                            WHERE order_id = %s
                                                        """, [sales_order_id])
                                                        invoice_result = cursor.fetchone()
                                                        
                                                        if invoice_result and invoice_result[0]:
                                                            sales_invoice_id = invoice_result[0]
                                                            print(f"Found sales_invoice_id {sales_invoice_id} for sales_order {sales_order_id}")
                                                    
                                                    # Handle service order type
                                                    elif service_order_id:
                                                        # Find corresponding service billing
                                                        cursor.execute("""
                                                            SELECT sb.service_billing_id
                                                            FROM services.delivery_order delivery
                                                            JOIN services.service_order_item soi ON delivery.service_order_item_id = soi.service_order_item_id
                                                            JOIN services.service_billing sb ON soi.service_order_item_id = sb.service_order_item_id
                                                            WHERE delivery.delivery_order_id = %s
                                                        """, [service_order_id])
                                                        billing_result = cursor.fetchone()
                                                        
                                                        if billing_result and billing_result[0]:
                                                            service_billing_id = billing_result[0]
                                                            print(f"Found service_billing_id {service_billing_id} for service_order {service_order_id}")
                            
                            # Create the billing receipt with appropriate IDs
                            if sales_invoice_id:
                                cursor.execute("""
                                    INSERT INTO distribution.billing_receipt
                                    (delivery_receipt_id, sales_invoice_id, service_billing_id, total_receipt)
                                    VALUES (%s, %s, %s, %s)
                                    RETURNING billing_receipt_id
                                """, [
                                    instance.delivery_receipt_id,
                                    sales_invoice_id,
                                    None,  # No service_billing_id for sales order
                                    total_amount
                                ])
                            elif service_billing_id:
                                cursor.execute("""
                                    INSERT INTO distribution.billing_receipt
                                    (delivery_receipt_id, sales_invoice_id, service_billing_id, total_receipt)
                                    VALUES (%s, %s, %s, %s)
                                    RETURNING billing_receipt_id
                                """, [
                                    instance.delivery_receipt_id,
                                    None,  # No sales_invoice_id for service order
                                    service_billing_id,
                                    total_amount
                                ])
                            else:
                                cursor.execute("""
                                    INSERT INTO distribution.billing_receipt
                                    (delivery_receipt_id, sales_invoice_id, service_billing_id, total_receipt)
                                    VALUES (%s, %s, %s, %s)
                                    RETURNING billing_receipt_id
                                """, [
                                    instance.delivery_receipt_id,
                                    None,  # No sales_invoice_id for internal delivery
                                    None,  # No service_billing_id for internal delivery
                                    total_amount
                                ])
                            
                            result = cursor.fetchone()
                            billing_receipt_id = result[0] if result else None
                            print(f"Created BillingReceipt {billing_receipt_id} for DeliveryReceipt {instance.delivery_receipt_id}")
                            
                            if sales_invoice_id:
                                print(f"  - Linked to sales_invoice_id: {sales_invoice_id}")
                            elif service_billing_id:
                                print(f"  - Linked to service_billing_id: {service_billing_id}")
                            
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
                                            SET goods_issue_id = %s, rework_id = NULL
                                            WHERE order_id = %s
                                        """, [goods_issue_id, sales_order_id])
                                        print(f"Updated sales.orders {sales_order_id} with goods_issue_id {goods_issue_id}")
    except Exception as e:
        print(f"Error handling delivery receipt update: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=DeliveryReceipt)
def handle_rejected_delivery(sender, instance, **kwargs):
    """
    When a DeliveryReceipt's receipt_status is 'Rejected':
    1. Create a Rejection record linked to that DeliveryReceipt if one doesn't exist
    """
    try:
        # Check if receipt_status is 'Rejected'
        if instance.receipt_status == 'Rejected':
            print(f"Processing rejected delivery receipt: {instance.delivery_receipt_id}")
            
            # First check if there's already a Rejection for this DeliveryReceipt
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT rejection_id
                    FROM distribution.rejection
                    WHERE delivery_receipt_id = %s
                """, [instance.delivery_receipt_id])
                result = cursor.fetchone()
                
                if result:
                    print(f"Found existing rejection: {result[0]}")
                else:
                    print("No existing rejection found, creating new one")
                
                # If no Rejection exists yet, create one
                if not result:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO distribution.rejection
                                (rejection_status, rejection_reason, rejection_date, delivery_receipt_id)
                                VALUES (%s, %s, %s, %s)
                                RETURNING rejection_id
                            """, [
                                'Pending',  # Default rejection_status
                                '',  # Empty rejection_reason to start with
                                date.today(),  # rejection_date is today
                                instance.delivery_receipt_id
                            ])
                            result = cursor.fetchone()
                            rejection_id = result[0] if result else None
                            print(f"Created Rejection {rejection_id} for DeliveryReceipt {instance.delivery_receipt_id}")
    except Exception as e:
        print(f"Error handling rejected delivery: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=DeliveryReceipt)
def update_customer_received_by(sender, instance, **kwargs):
    """
    Updates the received_by with the customer_id for sales orders when the receipt is received
    """
    try:
        # Only proceed if receipt_status is 'Received' and signature is provided
        if instance.receipt_status == 'Received' and instance.signature and instance.signature.strip():
            # Only proceed if received_by is not already set
            if not instance.received_by:
                with connection.cursor() as cursor:
                    # Trace back to find the customer for this delivery
                    # Note: Changed 'do' alias to 'delivery' to avoid SQL reserved keyword issue
                    cursor.execute("""
                        SELECT c.customer_id
                        FROM distribution.shipment_details sd
                        JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                        JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                        JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                        JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                        JOIN sales.orders o ON delivery.sales_order_id = o.order_id
                        JOIN sales.statement s ON o.statement_id = s.statement_id
                        JOIN sales.customers c ON s.customer_id = c.customer_id
                        WHERE sd.shipment_id = %s AND delivery.sales_order_id IS NOT NULL
                    """, [instance.shipment_id])
                    
                    customer_result = cursor.fetchone()
                    if customer_result and customer_result[0]:
                        customer_id = customer_result[0]
                        
                        # Update the received_by field
                        cursor.execute("""
                            UPDATE distribution.delivery_receipt
                            SET received_by = %s
                            WHERE delivery_receipt_id = %s
                        """, [customer_id, instance.delivery_receipt_id])
                        
                        print(f"Updated delivery receipt {instance.delivery_receipt_id} received_by to customer {customer_id}")
    except Exception as e:
        print(f"Error updating customer received_by: {str(e)}")
        traceback.print_exc()

@receiver(pre_save, sender=DeliveryReceipt)
def preserve_rejected_status(sender, instance, **kwargs):
    """
    Preserve the 'Rejected' status if it was explicitly set
    """
    try:
        # If this is an existing instance
        if instance.pk:
            # Get the current database state
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT receipt_status
                    FROM distribution.delivery_receipt
                    WHERE delivery_receipt_id = %s
                """, [instance.delivery_receipt_id])
                result = cursor.fetchone()
                
                # If the current status is 'Rejected', make sure it stays 'Rejected'
                if result and result[0] == 'Rejected':
                    print(f"Preserving 'Rejected' status for delivery receipt {instance.delivery_receipt_id}")
                    instance.receipt_status = 'Rejected'
    except Exception as e:
        print(f"Error in preserve_rejected_status: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=DeliveryReceipt)
def handle_rejection_reason_update(sender, instance, **kwargs):
    """
    Monitors Rejection records for changes to rejection_reason field.
    When a rejection_reason is filled, set status to Confirmed and create a ReworkOrder.
    """
    try:
        # Only process if this is a rejected receipt
        if instance.receipt_status == 'Rejected':
            with connection.cursor() as cursor:
                # Get the rejection record
                cursor.execute("""
                    SELECT rejection_id, rejection_reason, rejection_status
                    FROM distribution.rejection
                    WHERE delivery_receipt_id = %s
                """, [instance.delivery_receipt_id])
                
                rejection_result = cursor.fetchone()
                if rejection_result:
                    rejection_id = rejection_result[0]
                    rejection_reason = rejection_result[1]
                    rejection_status = rejection_result[2]
                    
                    print(f"Found rejection {rejection_id} with reason: '{rejection_reason}' and status: '{rejection_status}'")
    except Exception as e:
        print(f"Error handling rejection reason update: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=Rejection)
def handle_rejection_model_update(sender, instance, **kwargs):
    """
    When a Rejection's rejection_reason is updated from empty to non-empty:
    1. Update rejection_status to 'Confirmed'
    2. Create a ReworkOrder linked to that Rejection
    3. Update the related sales order with the rework_id if applicable
    """
    try:
        # Debug output
        print(f"Processing rejection: {instance.rejection_id}")
        print(f"Rejection reason: '{instance.rejection_reason}'")
        print(f"Rejection status: '{instance.rejection_status}'")
        
        # Check if rejection_reason is not empty and status is not already Confirmed
        if instance.rejection_reason and instance.rejection_reason.strip() and instance.rejection_status != 'Confirmed':
            print(f"Updating rejection status to 'Confirmed'")
            
            with connection.cursor() as cursor:
                # Update rejection status to Confirmed
                cursor.execute("""
                    UPDATE distribution.rejection
                    SET rejection_status = 'Confirmed'
                    WHERE rejection_id = %s
                """, [instance.rejection_id])
                
                # Check if ReworkOrder already exists for this rejection
                cursor.execute("""
                    SELECT rework_id
                    FROM distribution.rework_order
                    WHERE rejection_id = %s
                """, [instance.rejection_id])
                
                rework_result = cursor.fetchone()
                
                if rework_result:
                    print(f"Found existing ReworkOrder: {rework_result[0]}")
                else:
                    print(f"Creating new ReworkOrder for rejection {instance.rejection_id}")
                    
                    # If no ReworkOrder exists, create one
                    with transaction.atomic():
                        cursor.execute("""
                            INSERT INTO distribution.rework_order
                            (assigned_to, rework_status, rework_date, expected_completion, rejection_id, failed_shipment_id, rework_types)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            RETURNING rework_id
                        """, [
                            None,  # assigned_to will be filled later
                            'Pending',  # Default rework_status
                            date.today(),  # rework_date is today
                            None,  # expected_completion will be set later
                            instance.rejection_id,
                            None,  # failed_shipment_id is NULL as this is from a rejection
                            'Rejection'  # rework_types
                        ])
                        
                        result = cursor.fetchone()
                        rework_id = result[0] if result else None
                        print(f"Created ReworkOrder {rework_id} for Rejection {instance.rejection_id}")
                        
                        # If ReworkOrder was created, update sales order if applicable
                        if rework_id:
                            # Get the delivery_receipt_id associated with this rejection
                            delivery_receipt_id = instance.delivery_receipt_id
                            
                            # Trace back to find if this is a sales order delivery
                            cursor.execute("""
                                SELECT delivery.sales_order_id
                                FROM distribution.delivery_receipt dr
                                JOIN distribution.shipment_details sd ON dr.shipment_id = sd.shipment_id
                                JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                                JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                                JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                                JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                                WHERE dr.delivery_receipt_id = %s AND delivery.sales_order_id IS NOT NULL
                            """, [delivery_receipt_id])
                            
                            order_result = cursor.fetchone()
                            if order_result and order_result[0]:
                                sales_order_id = order_result[0]
                                
                                print(f"Updating sales.orders {sales_order_id} with rework_id {rework_id}")
                                
                                # Update the sales order with the rework_id
                                cursor.execute("""
                                    UPDATE sales.orders
                                    SET rework_id = %s, goods_issue_id = NULL
                                    WHERE order_id = %s
                                """, [rework_id, sales_order_id])
                                
                                print(f"Updated sales.orders {sales_order_id} with rework_id {rework_id}")
    except Exception as e:
        print(f"Error handling rejection update: {str(e)}")
        traceback.print_exc()