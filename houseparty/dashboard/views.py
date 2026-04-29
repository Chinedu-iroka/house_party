from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils.timezone import now
from django.db.models import Sum, Count
from events.models import Event, TicketTier
from registrations.models import Registration
from dashboard.models import AdminUser, AuditLog
import csv


def admin_login(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard_home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard_home')
        else:
            error = 'Invalid credentials or insufficient permissions.'

    return render(request, 'dashboard/login.html', {'error': error})


def admin_logout(request):
    logout(request)
    return redirect('admin_login')


@login_required(login_url='admin_login')
def dashboard_home(request):
    events = Event.objects.prefetch_related('tiers', 'registrations').order_by('-created_at')

    event_stats = []
    for event in events:
        confirmed = event.registrations.filter(status='CONFIRMED')
        revenue = confirmed.aggregate(total=Sum('amount_paid'))['total'] or 0
        event_stats.append({
            'event': event,
            'confirmed_count': confirmed.count(),
            'revenue': revenue,
        })

    return render(request, 'dashboard/home.html', {
        'event_stats': event_stats,
        'total_events': events.count(),
    })


@login_required(login_url='admin_login')
def event_create(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        form_data = request.POST.dict()
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        date = request.POST.get('date', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        zone = request.POST.get('zone', '').strip()
        full_address = request.POST.get('full_address', '').strip()

        if not name:
            errors['name'] = 'Event name is required.'
        if not description:
            errors['description'] = 'Description is required.'
        if not date:
            errors['date'] = 'Date is required.'
        if not start_time:
            errors['start_time'] = 'Start time is required.'
        if not zone:
            errors['zone'] = 'Zone is required.'
        if not full_address:
            errors['full_address'] = 'Full address is required.'

        # Validate tiers
        tier_names = request.POST.getlist('tier_name')
        tier_prices = request.POST.getlist('tier_price')
        tier_slots = request.POST.getlist('tier_slots')
        tier_inclusions = request.POST.getlist('tier_inclusions')

        if not tier_names or not any(t.strip() for t in tier_names):
            errors['tiers'] = 'At least one ticket tier is required.'

        if not errors:
            from datetime import date as d, time as t
            event = Event.objects.create(
                name=name,
                description=description,
                date=date,
                start_time=start_time,
                zone=zone,
                full_address=full_address,
                status=Event.Status.DRAFT,
            )

            for i, tier_name in enumerate(tier_names):
                if tier_name.strip():
                    TicketTier.objects.create(
                        event=event,
                        name=tier_name.strip(),
                        price=float(tier_prices[i]) if tier_prices[i] else 0,
                        total_slots=int(tier_slots[i]) if tier_slots[i] else 0,
                        inclusions=tier_inclusions[i].strip() if tier_inclusions[i] else '',
                    )

            _write_audit_log(request, AuditLog.Action.PUBLISH_EVENT, str(event.id), f"Event created: {event.name}")
            return redirect('admin_event_detail', event_id=event.id)

    return render(request, 'dashboard/event_create.html', {
        'errors': errors,
        'form_data': form_data,
    })


@login_required(login_url='admin_login')
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        date = request.POST.get('date', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        zone = request.POST.get('zone', '').strip()
        full_address = request.POST.get('full_address', '').strip()

        if not name: errors['name'] = 'Event name is required.'
        if not description: errors['description'] = 'Description is required.'
        if not date: errors['date'] = 'Date is required.'
        if not start_time: errors['start_time'] = 'Start time is required.'
        if not zone: errors['zone'] = 'Zone is required.'
        if not full_address: errors['full_address'] = 'Full address is required.'

        if not errors:
            event.name = name
            event.description = description
            event.date = date
            event.start_time = start_time
            event.zone = zone
            event.full_address = full_address
            event.save()
            return redirect('admin_event_detail', event_id=event.id)

    return render(request, 'dashboard/event_edit.html', {
        'event': event,
        'errors': errors,
    })


@login_required(login_url='admin_login')
def event_toggle_status(request, event_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    event = get_object_or_404(Event, id=event_id)
    new_status = request.POST.get('status')

    valid_statuses = [
        Event.Status.DRAFT,
        Event.Status.PUBLISHED,
        Event.Status.CLOSED,
    ]

    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    event.status = new_status
    event.save()

    _write_audit_log(request, AuditLog.Action.PUBLISH_EVENT, str(event.id), f"Status changed to {new_status}")
    return redirect('admin_event_detail', event_id=event.id)


@login_required(login_url='admin_login')
def event_detail_dashboard(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    registrations = Registration.objects.filter(
        event=event
    ).select_related('tier').order_by('-created_at')

    confirmed = registrations.filter(status='CONFIRMED')
    revenue = confirmed.aggregate(total=Sum('amount_paid'))['total'] or 0

    tier_stats = []
    for tier in event.tiers.all():
        tier_confirmed = confirmed.filter(tier=tier)
        tier_stats.append({
            'tier': tier,
            'confirmed': tier_confirmed.count(),
            'revenue': tier_confirmed.aggregate(t=Sum('amount_paid'))['t'] or 0,
            'available': tier.available_slots,
        })

    # Get all published events for next_event selector
    other_events = Event.objects.filter(
        status=Event.Status.PUBLISHED
    ).exclude(id=event_id)

    return render(request, 'dashboard/event_detail.html', {
        'event': event,
        'registrations': registrations,
        'confirmed_count': confirmed.count(),
        'revenue': revenue,
        'tier_stats': tier_stats,
        'other_events': other_events,
    })


@login_required(login_url='admin_login')
def event_export_csv(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    registrations = Registration.objects.filter(
        event=event, status='CONFIRMED'
    ).select_related('tier')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="registrants_{event.name}_{event.date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Full Name', 'Email', 'Phone', 'Tier', 'Amount Paid', 'Payment Reference', 'Registered At'])

    for reg in registrations:
        writer.writerow([
            reg.full_name,
            reg.email,
            reg.phone,
            reg.tier.name,
            reg.amount_paid,
            reg.payment_reference,
            reg.registered_at.strftime('%d %b %Y %I:%M %p') if reg.registered_at else '',
        ])

    return response


@login_required(login_url='admin_login')
def event_cancel(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'GET':
        next_events = Event.objects.filter(
            status=Event.Status.PUBLISHED
        ).exclude(id=event_id)
        return render(request, 'dashboard/event_cancel.html', {
            'event': event,
            'next_events': next_events,
        })

    if request.method == 'POST':
        next_event_id = request.POST.get('next_event_id')
        if not next_event_id:
            return render(request, 'dashboard/event_cancel.html', {
                'event': event,
                'next_events': Event.objects.filter(status=Event.Status.PUBLISHED).exclude(id=event_id),
                'error': 'Please select a next event for transfer.',
            })

        next_event = get_object_or_404(Event, id=next_event_id)
        _transfer_registrants(event, next_event, request)

        event.status = Event.Status.CANCELLED
        event.save()

        _write_audit_log(
            request,
            AuditLog.Action.CANCEL_EVENT,
            str(event.id),
            f"Cancelled and transferred to: {next_event.name}"
        )

        from communications.tasks import notify_transfer_task
        notify_transfer_task.delay(str(event.id), str(next_event.id))

        return redirect('admin_dashboard_home')


@login_required(login_url='admin_login')
def event_postpone(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'GET':
        next_events = Event.objects.filter(
            status=Event.Status.PUBLISHED
        ).exclude(id=event_id)
        return render(request, 'dashboard/event_postpone.html', {
            'event': event,
            'next_events': next_events,
        })

    if request.method == 'POST':
        next_event_id = request.POST.get('next_event_id')
        if not next_event_id:
            return render(request, 'dashboard/event_postpone.html', {
                'event': event,
                'next_events': Event.objects.filter(status=Event.Status.PUBLISHED).exclude(id=event_id),
                'error': 'Please select a next event for transfer.',
            })

        next_event = get_object_or_404(Event, id=next_event_id)
        _transfer_registrants(event, next_event, request)

        event.status = Event.Status.POSTPONED
        event.save()

        _write_audit_log(
            request,
            AuditLog.Action.POSTPONE_EVENT,
            str(event.id),
            f"Postponed and transferred to: {next_event.name}"
        )

        from communications.tasks import notify_transfer_task
        notify_transfer_task.delay(str(event.id), str(next_event.id))

        return redirect('admin_dashboard_home')


@login_required(login_url='admin_login')
def event_send_address(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'GET':
        return render(request, 'dashboard/event_send_address.html', {'event': event})

    if request.method == 'POST':
        # Reset address_sent flags so task re-sends to all
        Registration.objects.filter(
            event=event,
            status='CONFIRMED'
        ).update(address_sent=False)
        event.address_sent = False
        event.save()

        from communications.tasks import send_address_reveal_task
        send_address_reveal_task.delay(str(event.id))

        _write_audit_log(
            request,
            AuditLog.Action.MANUAL_ADDRESS_REVEAL,
            str(event.id),
            'Manual address reveal triggered'
        )

        return redirect('admin_event_detail', event_id=event.id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _transfer_registrants(from_event, to_event, request):
    confirmed = Registration.objects.filter(
        event=from_event,
        status=Registration.Status.CONFIRMED,
    )
    for reg in confirmed:
        # Match tier by name in new event, fallback to first tier
        matching_tier = to_event.tiers.filter(name=reg.tier.name).first()
        if not matching_tier:
            matching_tier = to_event.tiers.first()

        if matching_tier:
            Registration.objects.create(
                event=to_event,
                tier=matching_tier,
                full_name=reg.full_name,
                email=reg.email,
                phone=reg.phone,
                status=Registration.Status.CONFIRMED,
                payment_status=Registration.PaymentStatus.PAID,
                amount_paid=reg.amount_paid,
                payment_reference=reg.payment_reference,
            )

        reg.status = Registration.Status.TRANSFERRED
        reg.transferred_to = to_event
        reg.save()


def _write_audit_log(request, action, target, notes=''):
    try:
        admin = AdminUser.objects.get(user=request.user)
        AuditLog.objects.create(
            admin=admin,
            action=action,
            target=target,
            notes=notes,
        )
    except AdminUser.DoesNotExist:
        pass