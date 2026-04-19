from functools import wraps
from django.shortcuts import redirect


def age_verified_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('age_verified'):
            return redirect('age_gate')
        return view_func(request, *args, **kwargs)
    return wrapper