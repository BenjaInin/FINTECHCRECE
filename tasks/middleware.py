import time
from django.shortcuts import redirect
from django.contrib.auth import logout

class SessionIdleTimeout:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = int(time.time())
            last_activity = request.session.get('last_activity', current_time)

            if current_time - last_activity > 300:
                logout(request)
                return redirect('login')  # cambia por tu nombre de url

            request.session['last_activity'] = current_time

        return self.get_response(request)