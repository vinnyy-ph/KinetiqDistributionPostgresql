from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction, connection
from shipment.models import ShipmentDetails, FailedShipment, DeliveryReceipt, OperationalCost
import traceback
from datetime import date, timedelta  # Added timedelta import
from decimal import Decimal

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
            # Set shipment_date and estimated_arrival_date
            shipment_date = date.today()
            estimated_arrival_date = shipment_date + timedelta(days=2)
            
            # Update the shipment record with dates
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE distribution.shipment_details
                    SET shipment_date = %s, estimated_arrival_date = %s
                    WHERE shipment_id = %s
                """, [shipment_date, estimated_arrival_date, instance.shipment_id])
                print(f"Updated shipment {instance.shipment_id} with shipment_date: {shipment_date} and estimated_arrival_date: {estimated_arrival_date}")
                
                # After updating the dates in the shipment record, we should also update the sales.shipping_details if applicable
                # This will ensure the date fields are properly synchronized
                cursor.execute("""
                    SELECT delivery.sales_order_id
                    FROM distribution.shipment_details sd
                    JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                    JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                    JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                    JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                    WHERE sd.shipment_id = %s AND delivery.sales_order_id IS NOT NULL
                """, [instance.shipment_id])
                
                order_result = cursor.fetchone()
                if order_result and order_result[0]:
                    sales_order_id = order_result[0]
                    # Check if a shipping_details record exists
                    cursor.execute("""
                        SELECT shipping_id
                        FROM sales.shipping_details
                        WHERE order_id = %s
                    """, [sales_order_id])
                    
                    shipping_result = cursor.fetchone()
                    if shipping_result and shipping_result[0]:
                        # Update shipping_date and estimated_delivery on the existing record
                        cursor.execute("""
                            UPDATE sales.shipping_details
                            SET shipping_date = %s, estimated_delivery = %s
                            WHERE order_id = %s
                        """, [shipment_date, estimated_arrival_date, sales_order_id])
                        print(f"Updated shipping dates in sales.shipping_details for order {sales_order_id}")
            
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
                            # Check delivery types and set receiving_module accordingly
                            receiving_module = None
                            content_id = None
                            stock_transfer_id = None
                            
                            # Check if this is a content_id delivery or stock_transfer
                            cursor.execute("""
                                SELECT delivery.content_id, delivery.stock_transfer_id
                                FROM distribution.shipment_details sd
                                JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                                JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                                JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                                JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                                WHERE sd.shipment_id = %s
                            """, [instance.shipment_id])
                            
                            delivery_result = cursor.fetchone()
                            
                            if delivery_result:
                                content_id = delivery_result[0]
                                stock_transfer_id = delivery_result[1]
                                
                                # Case 1: This is a content_id delivery (from operations module)
                                if content_id:
                                    print(f"This is a content_id delivery: {content_id}")
                                    
                                    # Get the receiving_module from document_items
                                    cursor.execute("""
                                        SELECT receiving_module
                                        FROM operations.document_items
                                        WHERE content_id = %s
                                    """, [content_id])
                                    module_result = cursor.fetchone()
                                    
                                    if module_result and module_result[0]:
                                        receiving_module = module_result[0]
                                        print(f"Found receiving_module: {receiving_module}")
                                
                                # Case 2: This is a stock_transfer delivery (from inventory module)
                                elif stock_transfer_id:
                                    print(f"This is a stock_transfer delivery: {stock_transfer_id}")
                                    # Set receiving_module to Inventory for warehouse movements
                                    receiving_module = "Inventory"
                                    print(f"Setting receiving_module to: {receiving_module}")
                            
                            # Now include receiving_module when creating the delivery receipt
                            if receiving_module:
                                cursor.execute("""
                                    INSERT INTO distribution.delivery_receipt
                                    (delivery_date, received_by, signature, receipt_status, shipment_id, receiving_module)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    RETURNING delivery_receipt_id
                                """, [
                                    date.today(),
                                    None,  # received_by will be filled later
                                    '',  # Empty signature as requested (cannot be NULL)
                                    'Pending',  # Default receipt_status
                                    instance.shipment_id,
                                    receiving_module
                                ])
                            else:
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
                            if receiving_module:
                                print(f"  - With receiving_module: {receiving_module}")
            
            # Update associated PackingList status to 'Shipped'
            try:
                # Use a separate transaction for this operation
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Get the packing_list_id first
                        cursor.execute("""
                            SELECT packing_list_id 
                            FROM distribution.shipment_details 
                            WHERE shipment_id = %s
                        """, [instance.shipment_id])
                        packing_result = cursor.fetchone()
                        
                        if packing_result and packing_result[0]:
                            packing_list_id = packing_result[0]
                            print(f"Found packing_list_id {packing_list_id} for shipment {instance.shipment_id}")
                            
                            # Update packing status in a separate statement
                            cursor.execute("""
                                UPDATE distribution.packing_list 
                                SET packing_status = 'Shipped' 
                                WHERE packing_list_id = %s
                            """, [packing_list_id])
                            
                            if cursor.rowcount > 0:
                                print(f"Updated packing_list {packing_list_id} status to 'Shipped'")
                            else:
                                print(f"No update needed for packing_list {packing_list_id}")
            except Exception as e:
                print(f"Error updating packing status: {str(e)}")
                traceback.print_exc()
                # This error shouldn't prevent the rest of the processing
    except Exception as e:
        print(f"Error handling shipment status change: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=ShipmentDetails)
def update_sales_shipping_details(sender, instance, **kwargs):
    """
    When a ShipmentDetails record is created or updated for a sales order,
    update the corresponding record in sales.shipping_details
    """
    try:
        with connection.cursor() as cursor:
            # First, determine if this shipment is for a sales order and get the most current data
            cursor.execute("""
                SELECT 
                    delivery.sales_order_id, 
                    oc.operational_cost_id, 
                    c.service_type,
                    sd.shipment_date,
                    sd.estimated_arrival_date,
                    sd.tracking_number,
                    sd.shipment_status
                FROM distribution.shipment_details sd
                JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                LEFT JOIN distribution.operational_cost oc ON oc.shipping_cost_id = sd.shipping_cost_id
                LEFT JOIN distribution.carrier c ON sd.carrier_id = c.carrier_id
                WHERE sd.shipment_id = %s AND delivery.sales_order_id IS NOT NULL
            """, [instance.shipment_id])
            
            result = cursor.fetchone()
            
            if result and result[0]:
                sales_order_id = result[0]
                operational_cost_id = result[1]
                service_type = result[2] if len(result) > 2 and result[2] is not None else None
                
                # Get the most current date values directly from the database
                shipment_date = result[3]
                estimated_arrival_date = result[4]
                tracking_number = result[5]
                shipment_status = result[6]
                
                print(f"Found sales_order_id: {sales_order_id} for shipment {instance.shipment_id}")
                print(f"Current shipment_date: {shipment_date}, estimated_arrival_date: {estimated_arrival_date}")
                
                # Map shipment status to delivery status - only map normal statuses
                # Failed shipments and Rejected deliveries are handled separately
                delivery_status_map = {
                    'Pending': 'Pending',
                    'Shipped': 'Shipped', 
                    'Delivered': 'Delivered'
                }
                
                delivery_status = delivery_status_map.get(shipment_status, 'Pending')
                
                # Map service_type to shipping_method (assuming compatibility)
                # Default to 'Standard' if no match or if service_type is None
                shipping_method = 'Standard'
                if service_type == 'Express':
                    shipping_method = 'Express'
                elif service_type == 'Same-day':
                    shipping_method = 'Same-Day'
                
                # Check if there's already a shipping_details record for this order
                cursor.execute("""
                    SELECT shipping_id
                    FROM sales.shipping_details
                    WHERE order_id = %s
                """, [sales_order_id])
                
                shipping_details_result = cursor.fetchone()
                
                if shipping_details_result:
                    # Update existing record
                    shipping_id = shipping_details_result[0]
                    
                    cursor.execute("""
                        UPDATE sales.shipping_details
                        SET shipment_id = %s,
                            operational_cost_id = %s,
                            tracking_num = %s,
                            shipping_date = %s,
                            estimated_delivery = %s,
                            delivery_status = %s::delivery_status_enum,
                            shipping_method = %s::shipping_method_enum
                        WHERE shipping_id = %s
                    """, [
                        instance.shipment_id,
                        operational_cost_id,
                        tracking_number,
                        shipment_date,
                        estimated_arrival_date,
                        delivery_status,
                        shipping_method,
                        shipping_id
                    ])
                    
                    print(f"Updated sales.shipping_details {shipping_id} for order {sales_order_id}")
                else:
                    # Create a new record since one doesn't exist
                    # The trigger will generate the shipping_id
                    cursor.execute("""
                        INSERT INTO sales.shipping_details
                        (order_id, shipment_id, operational_cost_id, tracking_num, 
                         shipping_date, estimated_delivery, delivery_status, shipping_method)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::delivery_status_enum, %s::shipping_method_enum)
                        RETURNING shipping_id
                    """, [
                        sales_order_id,
                        instance.shipment_id,
                        operational_cost_id,
                        tracking_number,
                        shipment_date,
                        estimated_arrival_date,
                        delivery_status,
                        shipping_method
                    ])
                    
                    new_shipping_id = cursor.fetchone()[0]
                    print(f"Created new sales.shipping_details {new_shipping_id} for order {sales_order_id}")
    except Exception as e:
        print(f"Error updating sales shipping details: {str(e)}")
        traceback.print_exc()

@receiver(post_save, sender=DeliveryReceipt)
def handle_rejected_delivery_receipt(sender, instance, **kwargs):
    """
    When a DeliveryReceipt's status is set to 'Rejected':
    For sales orders, update shipping_details.delivery_status to 'Returned'
    The shipment_status remains unchanged since the shipment itself was successful
    """
    try:
        # Only proceed if receipt_status is 'Rejected'
        if instance.receipt_status == 'Rejected':
            print(f"Processing rejected delivery receipt {instance.delivery_receipt_id}")
            
            # Check if this delivery is for a sales order
            if instance.shipment_id:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT delivery.sales_order_id
                        FROM distribution.shipment_details sd
                        JOIN distribution.packing_list pl ON sd.packing_list_id = pl.packing_list_id
                        JOIN distribution.picking_list pkl ON pl.picking_list_id = pkl.picking_list_id
                        JOIN distribution.logistics_approval_request lar ON pkl.approval_request_id = lar.approval_request_id
                        JOIN distribution.delivery_order delivery ON lar.del_order_id = delivery.del_order_id
                        WHERE sd.shipment_id = %s AND delivery.sales_order_id IS NOT NULL
                    """, [instance.shipment_id])
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        sales_order_id = result[0]
                        
                        # Update the sales.shipping_details delivery_status to 'Returned'
                        cursor.execute("""
                            UPDATE sales.shipping_details
                            SET delivery_status = 'Returned'::delivery_status_enum
                            WHERE order_id = %s
                        """, [sales_order_id])
                        print(f"Updated sales.shipping_details delivery_status to 'Returned' for order {sales_order_id}")
    except Exception as e:
        print(f"Error handling rejected delivery receipt: {str(e)}")
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
                                    
                                    # Update actual_arrival_date on the associated shipment record
                                    cursor.execute("""
                                        UPDATE distribution.shipment_details
                                        SET actual_arrival_date = %s,
                                            shipment_status = 'Delivered'
                                        WHERE shipment_id = %s
                                    """, [date.today(), instance.shipment_id])
                                    print(f"Updated shipment {instance.shipment_id} with actual_arrival_date: {date.today()} and status: Delivered")
                                    
                                    # If this is a sales order delivery, also update the sales.shipping_details delivery_status
                                    if sales_order_id:
                                        cursor.execute("""
                                            UPDATE sales.shipping_details
                                            SET delivery_status = 'Delivered'::delivery_status_enum
                                            WHERE order_id = %s
                                        """, [sales_order_id])
                                        print(f"Updated sales.shipping_details delivery_status to 'Delivered' for order {sales_order_id}")
    except Exception as e:
        print(f"Error handling delivery receipt update: {str(e)}")
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

@receiver(pre_save, sender=OperationalCost)
def update_total_operational_cost(sender, instance, **kwargs):
    """
    Automatically recalculate total_operational_cost when any component changes,
    including additional_cost.
    """
    try:
        shipping_cost_total = Decimal('0.00')
        packing_cost_total = Decimal('0.00')
        additional = instance.additional_cost or Decimal('0.00')
        
        # Get shipping cost if it exists
        if instance.shipping_cost_id:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT total_shipping_cost
                    FROM distribution.shipping_cost
                    WHERE shipping_cost_id = %s
                """, [instance.shipping_cost_id])
                result = cursor.fetchone()
                if result and result[0]:
                    shipping_cost_total = result[0]
        
        # Get packing cost if it exists
        if instance.packing_cost_id:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT total_packing_cost
                    FROM distribution.packing_cost
                    WHERE packing_cost_id = %s
                """, [instance.packing_cost_id])
                result = cursor.fetchone()
                if result and result[0]:
                    packing_cost_total = result[0]
        
        # Calculate total
        instance.total_operational_cost = shipping_cost_total + packing_cost_total + additional
        print(f"Recalculated operational cost: {instance.total_operational_cost} = {shipping_cost_total} + {packing_cost_total} + {additional}")
        
    except Exception as e:
        print(f"Error updating total operational cost: {str(e)}")
        traceback.print_exc()