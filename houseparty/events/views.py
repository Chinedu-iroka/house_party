from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Event, TicketTier
from .decorators import age_verified_required


def age_gate(request):
    if request.session.get('age_verified'):
        return redirect('homepage')

    if request.method == 'POST':
        answer = request.POST.get('age_confirm')
        if answer == 'yes':
            request.session['age_verified'] = True
            return redirect('homepage')
        else:
            return redirect('age_exit')

    return render(request, 'public/age_gate.html')


def age_exit(request):
    return render(request, 'public/age_exit.html')


@age_verified_required
def homepage(request):
    events = Event.objects.filter(
        status=Event.Status.PUBLISHED
    ).prefetch_related('tiers')

    events_with_slots = []
    for event in events:
        tiers_data = []
        all_sold_out = True

        for tier in event.tiers.all():
            available = tier.available_slots
            if available > 0:
                all_sold_out = False
            tiers_data.append({
                'tier': tier,
                'available': available,
                'fill_percentage': tier.fill_percentage,
                'is_sold_out': tier.is_sold_out,
            })

        events_with_slots.append({
            'event': event,
            'tiers': tiers_data,
            'is_sold_out': all_sold_out,
        })

    return render(request, 'public/homepage.html', {
        'events': events_with_slots,
    })


@age_verified_required
def event_detail(request, event_id):
    event = get_object_or_404(
        Event,
        id=event_id,
        status=Event.Status.PUBLISHED
    )

    tiers_data = []
    for tier in event.tiers.all():
        tiers_data.append({
            'tier': tier,
            'available': tier.available_slots,
            'fill_percentage': tier.fill_percentage,
            'is_sold_out': tier.is_sold_out,
        })

    return render(request, 'public/event_detail.html', {
        'event': event,
        'tiers': tiers_data,
    })


def slot_count_api(request, tier_id):
    try:
        tier = TicketTier.objects.get(id=tier_id)
    except TicketTier.DoesNotExist:
        return JsonResponse({'error': 'Tier not found'}, status=404)

    available = tier.available_slots

    return JsonResponse({
        'tier_id': str(tier_id),
        'available': available,
        'total': tier.total_slots,
        'sold_out': tier.is_sold_out,
        'fill_percentage': tier.fill_percentage,
    })


def custom_404(request, exception):
    return render(request, '404.html', status=404)