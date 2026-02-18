from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import TypingResult
import random
import requests


# ---------------- IMAGE TEXT DATA ----------------
IMAGE_TEXTS = {
    15: [
        {"image": "img_2.jpg", "text": "Just as with a traditional book, you can also highlight  favorite passages, add notes, and create bookmarks."},
    ],
    30: [
        {"image": "img1.jpg", "text": "Be such  a man,  and live  such a life,that if every man were  such as you and every life a life like yours, this earth would be  God,s  paradise"},
    ],
    60: [
        {"image": "img3.jpg", "text": "Nature reveals to us a beautiful  part of  ourselves we could not find anywhere else."},
    ],
}


# ---------------- GRAMMAR CHECK ----------------
def grammar_check(text):
    url = "https://api.languagetool.org/v2/check"
    data = {"text": text, "language": "en-US"}

    try:
        response = requests.post(url, data=data)
        result = response.json()

        errors = []
        for match in result.get("matches", []):
            errors.append({
                "message": match["message"],
                "suggestions": [r["value"] for r in match.get("replacements", [])[:3]]
            })
        return errors
    except:
        return []


# ---------------- HOME VIEW ----------------
def home(request):

     # ---- FREE TRIAL CHECK ----
    if not request.user.is_authenticated:
        trial_used = request.session.get("trial_used", False)

        if trial_used:
            return redirect("login")   # force login after trial
    # -------- AJAX IMAGE CHANGE --------
    if request.GET.get("get_text"):
        seconds = int(request.GET.get("get_text", 60))

        options = IMAGE_TEXTS.get(seconds, IMAGE_TEXTS[60])
        data = random.choice(options)

        return JsonResponse({
            "image": data["image"],
            "paragraph": data["text"]
        })

    # -------- SUBMIT TEST --------
    if request.method == "POST":
        paragraph = request.POST.get("paragraph_text")
        typed_text = request.POST.get("typed_text")
        time_taken = float(request.POST.get("time_taken", 60))

        if not request.user.is_authenticated:
          request.session["trial_used"] = True


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

        # Grammar
        grammar_errors = grammar_check(typed_text)
        grammar_score = max(0, 100 - len(grammar_errors) * 10)

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

    # -------- NORMAL PAGE LOAD --------
    data = random.choice(IMAGE_TEXTS[60])

    return render(request, "home.html", {
        "image_path":  "images/typing/" + data["image"],
        "paragraph": data["text"]
    })


def try_again(request):

    # If user not logged AND trial already used
    if not request.user.is_authenticated:
        if request.session.get("trial_used"):
            return redirect("login")

    # otherwise allow test again
    return redirect("home")





#----- result view-----
def result(request):


    return render(request, "result.html", context)

   
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
