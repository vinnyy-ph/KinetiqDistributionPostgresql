from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction, connection
from packing.models import PackingList, PackingCost
import traceback

@receiver(pre_save, sender=PackingCost)
def calculate_total_packing_cost(sender, instance, **kwargs):
    """
    Automatically calculate total_packing_cost before saving
    """
    instance.total_packing_cost = instance.material_cost + instance.labor_cost

@receiver(post_save, sender=PackingList)
def create_shipment_data(sender, instance, **kwargs):
    """
    When a PackingList is marked as 'Packed', 
    automatically create associated ShippingCost and ShipmentDetails
    """
    if instance.packing_status == 'Packed':
        try:
            with transaction.atomic():
                # Use direct SQL to insert ShippingCost and get the ID
                with connection.cursor() as cursor:
                    # Generate a unique shipping_cost_id
                    cursor.execute("""
                        INSERT INTO distribution.shipping_cost 
                        (packing_list_id, cost_per_kg, cost_per_km, weight_kg, distance_km, total_shipping_cost)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING shipping_cost_id
                    """, [
                        instance.packing_list_id, 
                        0.00,  # Default cost_per_kg
                        0.00,  # Default cost_per_km
                        0.00,  # Default weight_kg
                        0.00,  # Default distance_km
                        0.00   # Default total_shipping_cost
                    ])
                    shipping_cost_id = cursor.fetchone()[0]

                    # Create ShipmentDetails using the generated shipping_cost_id
                    cursor.execute("""
                        INSERT INTO distribution.shipment_details 
                        (shipment_date, shipment_status, tracking_number, packing_list_id, shipping_cost_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING shipment_id
                    """, [
                        None,  # shipment_date starts as NULL
                        'Pending',  # Default shipment_status 
                        'TRK' + instance.packing_list_id[-8:],  # Generate simple tracking number
                        instance.packing_list_id,
                        shipping_cost_id
                    ])
                    shipment_id = cursor.fetchone()[0]
                
                print(f"Created ShippingCost and ShipmentDetails for PackingList {instance.packing_list_id}")
        
        except Exception as e:
            print(f"Detailed Error creating shipment data: {str(e)}")
            traceback.print_exc()