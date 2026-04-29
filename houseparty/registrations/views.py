import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils.timezone import now
from datetime import timedelta
from events.models import Event, TicketTier
from .models import Registration
from .slot import reserve_slot, SlotUnavailableError
from .paystack import initialize_payment


def register(request, event_id, tier_id):
    if not request.session.get('age_verified'):
        return redirect('age_gate')

    event = get_object_or_404(Event, id=event_id, status=Event.Status.PUBLISHED)
    tier = get_object_or_404(TicketTier, id=tier_id, event=event)

    # Pre-check before showing form
    if tier.is_sold_out:
        return render(request, 'public/sold_out.html', {'event': event, 'tier': tier})

    errors = {}
    form_data = {}

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email     = request.POST.get('email', '').strip()
        phone     = request.POST.get('phone', '').strip()
        tc_agreed = request.POST.get('tc_agreed')

        form_data = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
        }

        # Validate
        if not full_name or len(full_name) < 2:
            errors['full_name'] = 'Please enter your full name.'

        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            errors['email'] = 'Please enter a valid email address.'

        if not phone or len(phone) < 10:
            errors['phone'] = 'Please enter a valid phone number.'

        if not tc_agreed:
            errors['tc_agreed'] = 'You must agree to the Terms & Conditions.'

        if not errors:
            # Attempt slot reservation
            try:
                reserve_slot(tier)
            except SlotUnavailableError:
                return render(request, 'public/sold_out.html', {
                    'event': event,
                    'tier': tier
                })

            # Generate unique payment reference
            payment_reference = f"HP-{uuid.uuid4().hex[:12].upper()}"

            # Create pending registration
            registration = Registration.objects.create(
                event=event,
                tier=tier,
                full_name=full_name,
                email=email,
                phone=phone,
                status=Registration.Status.PENDING,
                payment_status=Registration.PaymentStatus.UNPAID,
                payment_reference=payment_reference,
                reservation_expires_at=now() + timedelta(minutes=10),
            )

            # Initialise Paystack payment
            payment_url = initialize_payment(
                reference=payment_reference,
                amount=tier.price,
                email=email,
                registration_id=str(registration.id),
            )

            if payment_url:
                return redirect(payment_url)
            else:
                # Paystack init failed — release slot and show error
                from .slot import release_slot
                release_slot(tier)
                registration.delete()
                errors['general'] = 'Payment could not be initiated. Please try again.'

    return render(request, 'public/register.html', {
        'event': event,
        'tier': tier,
        'errors': errors,
        'form_data': form_data,
    })


def checkout(request, registration_id):
    if not request.session.get('age_verified'):
        return redirect('age_gate')

    registration = get_object_or_404(
        Registration,
        id=registration_id,
        status=Registration.Status.PENDING
    )
    return render(request, 'public/checkout.html', {
        'registration': registration,
    })


def registration_success(request, registration_id):
    registration = get_object_or_404(
        Registration,
        id=registration_id,
        status=Registration.Status.CONFIRMED
    )
    return render(request, 'public/registration_success.html', {
        'registration': registration,
    })


def registration_failed(request):
    return render(request, 'public/registration_failed.html')


def release_slot_api(request, registration_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        registration = Registration.objects.get(
            id=registration_id,
            status=Registration.Status.PENDING
        )
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)

    from .slot import release_slot
    release_slot(registration.tier)
    registration.status = Registration.Status.CANCELLED
    registration.save()

    return JsonResponse({'success': True})