from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from delivery.models import DeliveryOrder, LogisticsApprovalRequest

class Command(BaseCommand):
    help = 'Synchronizes delivery orders with source records'

    def handle(self, *args, **options):
        self.stdout.write('Starting delivery order synchronization...')
        
        # Check for new orders of each type
        self.sync_sales_orders()
        self.sync_service_orders()
        self.sync_stock_transfers()
        self.sync_document_items()
        
        self.stdout.write(self.style.SUCCESS('Delivery order synchronization completed'))
    
    def sync_sales_orders(self):
        with connection.cursor() as cursor:
            # Find sales orders that don't have delivery orders
            cursor.execute("""
                SELECT order_id
                FROM sales.orders o
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM distribution.delivery_order d
                    WHERE d.sales_order_id = o.order_id
                )
            """)
            sales_orders = cursor.fetchall()
            
            self.stdout.write(f'Found {len(sales_orders)} new sales orders')
            
            for order in sales_orders:
                order_id = order[0]
                self.create_delivery_order(order_id, 'sales_order', True)
    
    def sync_service_orders(self):
        with connection.cursor() as cursor:
            # Find service orders that don't have delivery orders
            cursor.execute("""
                SELECT delivery_order_id
                FROM services.delivery_order o
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM distribution.delivery_order d
                    WHERE d.service_order_id = o.delivery_order_id
                )
            """)
            service_orders = cursor.fetchall()
            
            self.stdout.write(f'Found {len(service_orders)} new service orders')
            
            for order in service_orders:
                order_id = order[0]
                self.create_delivery_order(order_id, 'service_order', True)
    
    def sync_stock_transfers(self):
        with connection.cursor() as cursor:
            # Find stock transfers that don't have delivery orders
            cursor.execute("""
                SELECT adjustment_id
                FROM inventory.inventory_adjustments ia
                WHERE ia.adjustment_type = 'Outbound-Distribution'
                AND NOT EXISTS (
                    SELECT 1
                    FROM distribution.delivery_order d
                    WHERE d.stock_transfer_id = ia.adjustment_id
                )
            """)
            transfers = cursor.fetchall()
            
            self.stdout.write(f'Found {len(transfers)} new stock transfers')
            
            for transfer in transfers:
                transfer_id = transfer[0]
                self.create_delivery_order(transfer_id, 'stock_transfer', False)
    
    def sync_document_items(self):
        with connection.cursor() as cursor:
            # Find document items that don't have delivery orders
            cursor.execute("""
                SELECT content_id
                FROM operations.document_items di
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM distribution.delivery_order d
                    WHERE d.content_id = di.content_id
                )
            """)
            items = cursor.fetchall()
            
            self.stdout.write(f'Found {len(items)} new document items')
            
            for item in items:
                item_id = item[0]
                self.create_delivery_order(item_id, 'content', False)
    
    def create_delivery_order(self, source_id, source_type, is_external):
        try:
            del_type = 'External Delivery' if is_external else 'Internal Delivery'
            
            # Create delivery kwargs with appropriate field set
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
            
            # Create the delivery order WITHOUT initially setting approval_request
            delivery_order = DeliveryOrder.objects.create(**delivery_kwargs)
            
            # Now create logistics approval request with del_order set to the delivery order we just created
            approval_request = LogisticsApprovalRequest.objects.create(
                request_date=timezone.now().date(),
                approval_status='Pending',
                del_order=delivery_order  # This links the approval request to the delivery order
            )
            
            # Now update the delivery order to link back to the approval request
            delivery_order.approval_request = approval_request
            delivery_order.save(update_fields=['approval_request'])
            
            self.stdout.write(f'Created delivery order for {source_type} {source_id}')
            return delivery_order
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating delivery order for {source_type} {source_id}: {str(e)}'))
            return None