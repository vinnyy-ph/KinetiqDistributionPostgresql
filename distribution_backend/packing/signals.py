from django.db.models.signals import pre_save
from django.dispatch import receiver
from packing.models import PackingCost

@receiver(pre_save, sender=PackingCost)
def calculate_total_packing_cost(sender, instance, **kwargs):
    """
    Automatically calculate total_packing_cost before saving
    """
    instance.total_packing_cost = instance.material_cost + instance.labor_cost