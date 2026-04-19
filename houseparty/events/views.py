from django.shortcuts import render, redirect
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
    if not request.session.get('age_verified'):
        return redirect('age_gate')
    return render(request, 'public/homepage.html')