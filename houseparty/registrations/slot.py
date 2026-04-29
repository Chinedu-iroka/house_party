from django.db import transaction


class SlotUnavailableError(Exception):
    pass


def reserve_slot(tier):
    with transaction.atomic():
        # Lock this specific row — all competing requests wait here
        from events.models import TicketTier
        locked_tier = TicketTier.objects.select_for_update().get(id=tier.id)

        available = (
            locked_tier.total_slots
            - locked_tier.reserved_slots
            - locked_tier.confirmed_slots
        )

        if available <= 0:
            raise SlotUnavailableError("No slots available for this tier.")

        locked_tier.reserved_slots += 1
        locked_tier.save()


def release_slot(tier):
    with transaction.atomic():
        from events.models import TicketTier
        locked_tier = TicketTier.objects.select_for_update().get(id=tier.id)
        locked_tier.reserved_slots = max(0, locked_tier.reserved_slots - 1)
        locked_tier.save()


def confirm_slot(tier):
    with transaction.atomic():
        from events.models import TicketTier
        locked_tier = TicketTier.objects.select_for_update().get(id=tier.id)
        locked_tier.reserved_slots = max(0, locked_tier.reserved_slots - 1)
        locked_tier.confirmed_slots += 1
        locked_tier.save()