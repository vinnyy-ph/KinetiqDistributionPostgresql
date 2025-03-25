from django.db import transaction
from django.utils import timezone
from .models import DeliveryOrder, LogisticsApprovalRequest

def create_delivery_order(source_id, source_type, is_external=False):
    """
    Function to be called by other modules when they want to create a delivery order.
    
    Parameters:
    - source_id: The ID of the source record (sales order, service order, etc.)
    - source_type: String identifying the type ('sales_order', 'service_order', 'stock_transfer', 'content')
    - is_external: Boolean indicating if this is an external delivery (True for sales_order and service_order)
    
    Returns:
    - The created DeliveryOrder instance
    
    Example usage from other modules:
    
    from delivery.signals import create_delivery_order
    
    # After creating a sales order:
    create_delivery_order(sales_order.id, 'sales_order', is_external=True)
    
    # After creating a service order:
    create_delivery_order(service_order.id, 'service_order', is_external=True)
    
    # After creating a stock transfer:
    create_delivery_order(stock_transfer.id, 'stock_transfer', is_external=False)
    
    # After creating document items:
    create_delivery_order(content.id, 'content', is_external=False)
    """
    with transaction.atomic():
        # Determine delivery type based on is_external flag
        del_type = 'External Delivery' if is_external else 'Internal Delivery'
        
        # Create delivery order with appropriate field set
        delivery_kwargs = {
            'order_status': 'Created',
            'del_type': del_type
        }
        
        # Set the appropriate ID field based on source_type
        if source_type == 'sales_order':
            delivery_kwargs['sales_order_id'] = source_id
        elif source_type == 'service_order':
            delivery_kwargs['service_order_id'] = source_id
        elif source_type == 'stock_transfer':
            delivery_kwargs['stock_transfer_id'] = source_id
        elif source_type == 'content':
            delivery_kwargs['content_id'] = source_id
        else:
            raise ValueError(f"Invalid source_type: {source_type}. Must be one of: 'sales_order', 'service_order', 'stock_transfer', 'content'")
        
        # Create the delivery order first
        delivery_order = DeliveryOrder.objects.create(**delivery_kwargs)
        
        # Create logistics approval request
        approval_request = LogisticsApprovalRequest.objects.create(
            request_date=timezone.now().date(),
            approval_status='Pending',
            del_order=delivery_order
        )
        
        # Update delivery order with approval request reference
        # This handles the circular reference between the two models
        delivery_order.approval_request = approval_request
        delivery_order.save(update_fields=['approval_request'])
        
        return delivery_order


def create_delivery_order_for_sales(sales_order_id):
    """
    Convenience method for creating delivery orders from sales orders.
    """
    return create_delivery_order(sales_order_id, 'sales_order', is_external=True)


def create_delivery_order_for_service(service_order_id):
    """
    Convenience method for creating delivery orders from service orders.
    """
    return create_delivery_order(service_order_id, 'service_order', is_external=True)


def create_delivery_order_for_transfer(stock_transfer_id):
    """
    Convenience method for creating delivery orders from stock transfers.
    """
    return create_delivery_order(stock_transfer_id, 'stock_transfer', is_external=False)


def create_delivery_order_for_content(content_id):
    """
    Convenience method for creating delivery orders from document items.
    """
    return create_delivery_order(content_id, 'content', is_external=False)