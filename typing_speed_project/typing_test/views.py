from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import TypingResult
import random
import requests

TIME_TEXTS = {
    15: ["The sun is shining brightly today .", "A quick brown fox jumps over the lazy dog in the middle of a green field.", "Reading a good book is a great way to relax after a long day at work."],
    30: ["Nature is beautiful and it is a gift to us. flowers makes the world a better place to live.", "A healthy lifestyle is very important. Eating fresh fruit and vegetables every day helps you feel happy and gives you the energy to play outside."],
    60: ["Success is not about how fast you go, but about not stopping. Every small step you take brings you closer to your goal. If you practice something every day, you will eventually become very good at it. ","Traveling to new places is an amazing experience. You get to see how other people live and try different kinds of food. Whether you go to a busy city or a quiet mountain, there is always something new to learn."]
}


# ---------------- GRAMMAR CHECK ----------------
def grammar_check(text):
    url = "https://api.languagetool.org/v2/check"
    data = {'text': text, 'language': 'en-US'}
    try:
        response = requests.post(url, data=data)
        result = response.json()
        errors = []
        for match in result.get('matches', []):
            errors.append({
                'message': match['message'],
                'suggestions': [s['value'] for s in match.get('replacements', [])[:3]]
            })
        return errors
    except:
        return []

# ---------------- HOME VIEW ----------------
def home(request):

    # ---------------- AJAX paragraph change ----------------
    if request.GET.get("get_text"):
        seconds = int(request.GET.get("get_text"))
        return JsonResponse({
            "paragraph": random.choice(TIME_TEXTS.get(seconds))
        })

    # ---------------- POST (Submit Test) ----------------
    if request.method == "POST":

        paragraph = request.POST.get("paragraph_text")
        typed_text = request.POST.get("typed_text")
        time_taken = float(request.POST.get("time_taken", 60))

        # WPM
        time_minutes = time_taken / 60
        wpm = round((len(typed_text) / 5) / time_minutes) if time_minutes > 0 else 0

        # Accuracy
        para_words = paragraph.split()
        typed_words = typed_text.split()
        correct = sum(
            1 for i in range(min(len(para_words), len(typed_words)))
            if para_words[i] == typed_words[i]
        )
        accuracy = round((correct / len(para_words)) * 100, 2) if para_words else 0

        grammar_errors = grammar_check(typed_text)
        grammar_score = max(0, 100 - len(grammar_errors) * 10)

        # ✅ Mark trial used AFTER submission
        if not request.user.is_authenticated:
            request.session["trial_used"] = True

        if request.user.is_authenticated:
            TypingResult.objects.create(
                user=request.user,
                wpm=wpm,
                accuracy=accuracy,
                grammar_score=grammar_score
            )

        return render(request, "result.html", {
            "wpm": wpm,
            "accuracy": accuracy,
            "grammar_score": grammar_score,
            "paragraph": paragraph,
            "typed_text": typed_text,
            "grammar_errors": grammar_errors
        })

    # ---------------- GET (Open Test Page) ----------------
    if request.user.is_authenticated:
        if request.session.get("trial_used"):
            return redirect("login")

    paragraph = random.choice(TIME_TEXTS[60])
    return render(request, "home.html", {"paragraph": paragraph})

# ---------------- SIGNUP ----------------
def signup_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            return render(request, "signup.html", {"error": "Passwords do not match"})

        if User.objects.filter(username=email).exists():
            return render(request, "signup.html", {"error": "User already exists"})

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        return redirect("login")

    return render(request, "signup.html")


# ---------------- LOGIN ----------------
def login_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            request.session.pop("trial_used", None)
            return redirect("home")

        return render(request, "login.html", {"error": "Invalid credentials"})

    return render(request, "login.html")


# ---------------- LOGOUT ----------------
def logout_view(request):
    logout(request)
    return redirect("home")
