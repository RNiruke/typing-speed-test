from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import TypingResult, ImageInfo

from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone

# ✅ NEW imports for email verification
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings





from difflib import SequenceMatcher
import pytesseract
import random
import requests
import re


# ------ Grammar Rules ------
ARTICLES = {"a", "an", "the"}
BE_VERBS = {"is", "am", "are", "was", "were", "have", "had"}


def clean_words(text):
    text = re.sub(r"[^\w\s]", "", text)
    return text.split()


def target_rule_grammar(target, typed):
    target_words = clean_words(target)
    typed_words  = clean_words(typed)
    issues = []
    sm = SequenceMatcher(None, target_words, typed_words)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            for t_word, u_word in zip(target_words[i1:i2], typed_words[j1:j2]):
                if t_word.lower() in ARTICLES or u_word.lower() in ARTICLES:
                    issues.append({"message": "Article mistake based on target text", "wrong": u_word, "suggestions": [t_word]})
                elif t_word.lower() in BE_VERBS or u_word.lower() in BE_VERBS:
                    issues.append({"message": "Verb form mistake based on target text", "wrong": u_word, "suggestions": [t_word]})
                elif u_word.isupper() and u_word.lower() == t_word.lower():
                    issues.append({"message": "Word typed in uppercase", "wrong": u_word, "suggestions": [t_word]})
                elif u_word.lower() != t_word.lower():
                    issues.append({"message": "Spelling mistake", "wrong": u_word, "suggestions": [t_word]})
    return issues


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def no_cache(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"]        = "no-cache"
    response["Expires"]       = "0"
    return response


# ================================================================
# WHOAMI
# ================================================================
def whoami(request):
    username = request.user.username if request.user.is_authenticated else ""
    return JsonResponse({"username": username})


# ================================================================
# CSRF TOKEN
# ================================================================
@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"csrftoken": get_token(request)})


# ================================================================
# ✅ HELPER: Send verification email
#
# How it works:
#   1. Encodes the user's primary key into a URL-safe base64 string (uidb64)
#   2. Generates a secure one-time token tied to the user's password hash + last_login
#   3. Builds a full activation URL and emails it to the user
#   4. The token automatically expires after PASSWORD_RESET_TIMEOUT (default 24h)
# ================================================================
def send_verification_email(request, user):
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link  = request.build_absolute_uri(f"/activate/{uid}/{token}/")

    send_mail(
        subject="Activate your TypingTest account",
        message=(
            f"Hi {user.first_name},\n\n"
            f"Thanks for signing up! Click the link below to activate your account:\n\n"
            f"{link}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you did not sign up, ignore this email.\n\n"
            f"— TypingTest Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ================================================================
# ✅ ACTIVATE ACCOUNT
#
# Called when user clicks the link in their email.
# Decodes the uid, validates the token, and sets is_active = True.
# Shows success page on valid token, error page on invalid/expired.
# ================================================================
def activate(request, uidb64, token):
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if user.is_active:
            # Already activated — just go to login
            return redirect("login")
        user.is_active = True
        user.save()
        return render(request, "activation_success.html")
    else:
        return render(request, "activation_invalid.html")


# ================================================================
# HOME
# ================================================================
@never_cache
def home(request):
    if not request.user.is_authenticated:
        if request.session.get("trial_used"):
            return redirect("login")

    if request.GET.get("get_image"):
        seconds  = int(request.GET.get("get_image"))
        images   = ImageInfo.objects.filter(time_limit=seconds)
        selected = random.choice(list(images))
        return JsonResponse({"image": selected.image.url, "paragraph": selected.extracted_text})

    if request.method == "POST":
        paragraph  = request.POST.get("paragraph_text", "")
        typed_text = request.POST.get("typed_text", "")
        timeLimit  = int(request.POST.get("test_time", 60))
        time_taken = float(request.POST.get("time_taken", 60))

        if not request.user.is_authenticated:
            request.session["trial_used"] = True

        minutes = time_taken / 60
        wpm     = round((len(typed_text) / 5) / minutes) if minutes else 0

        p_words  = paragraph.split()
        t_words  = typed_text.split()
        correct  = sum(1 for i in range(min(len(p_words), len(t_words))) if p_words[i] == t_words[i])
        accuracy = round((correct / len(p_words)) * 100, 2) if len(p_words) else 0

        all_errors    = target_rule_grammar(paragraph, typed_text)
        grammar_score = max(0, 100 - len(all_errors) * 10)

        if request.user.is_authenticated:
            TypingResult.objects.create(
                user=request.user, wpm=wpm, accuracy=accuracy,
                grammar_score=grammar_score, time_limit=timeLimit, test_time=time_taken
            )

        wrong_words       = [e.get("wrong", "") for e in all_errors]
        highlighted_words = []
        for word in typed_text.split():
            if word in wrong_words:
                highlighted_words.append(f'<span style="color:red;font-weight:600">{word}</span>')
            else:
                highlighted_words.append(word)

        return no_cache(render(request, "result.html", {
            "wpm": wpm, "accuracy": accuracy, "grammar_score": grammar_score,
            "grammar_errors": all_errors, "paragraph": paragraph,
            "typed_text": typed_text, "highlighted_text": " ".join(highlighted_words),
        }))

    images   = ImageInfo.objects.filter(time_limit=60)
    selected = random.choice(list(images))
    return no_cache(render(request, "home.html", {
        "image_path": selected.image.url, "paragraph": selected.extracted_text, "selected_time": 60
    }))


# ================================================================
# TRY AGAIN
# ================================================================
@never_cache
def try_again(request):
    if not request.user.is_authenticated and request.session.get("trial_used"):
        return redirect("login")
    return no_cache(redirect("home"))


# ================================================================
# ✅ LOGIN — blocks unverified (is_active=False) users
# ================================================================
@never_cache
def login_view(request):
    if request.method == "POST":
        email    = request.POST["email"]
        password = request.POST["password"]
        user     = authenticate(request, username=email, password=password)

        if user:
            if not user.is_active:
                # User exists but hasn't clicked the email link yet
                return no_cache(render(request, "login.html", {
                    "error": "Account not activated. Please check your email for the activation link."
                }))
            login(request, user)
            request.session.pop("trial_used", None)
            rotate_token(request)
            return no_cache(redirect("home"))

        return no_cache(render(request, "login.html", {"error": "Invalid credentials"}))

    return no_cache(render(request, "login.html"))


# ================================================================
# ✅ SIGNUP — saves user as inactive, sends verification email
# ================================================================
@never_cache
def signup_view(request):
    if request.method == "POST":
        email            = request.POST["email"]
        first_name       = request.POST["first_name"]
        last_name        = request.POST["last_name"]
        password         = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            return no_cache(render(request, "signup.html", {"error": "Passwords do not match"}))

        if User.objects.filter(username=email).exists():
            return no_cache(render(request, "signup.html", {"error": "User already exists"}))

        # ✅ Create user as INACTIVE — cannot login until email verified
        user            = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = first_name
        user.last_name  = last_name
        user.is_active  = False
        user.save()

        # ✅ Send the activation email
        send_verification_email(request, user)

        return render(request, "verify_email_sent.html", {"email": email})

    return no_cache(render(request, "signup.html"))


# ================================================================
# LOGOUT
# ================================================================
@never_cache
def logout_view(request):
    logout(request)
    return no_cache(redirect("home"))


# ================================================================
# PERFORMANCE DASHBOARD
# ================================================================
@never_cache
@login_required
def performance(request):
    filter_time = request.GET.get("time", "all")
    results     = TypingResult.objects.filter(user=request.user).order_by("created_at")
    if filter_time != "all":
        results = results.filter(time_limit=int(filter_time))

    total_tests    = results.count()
    total_time     = results.aggregate(Sum("test_time"))["test_time__sum"] or 0
    recent_results = results.order_by("-created_at")[:8]
    graph_data     = results.order_by("created_at")
    graph_labels   = [timezone.localtime(r.created_at).strftime("%d/%m/%Y %I:%M %p") for r in graph_data]
    graph_wpm      = [r.wpm for r in graph_data]

    total_typing_seconds = TypingResult.objects.filter(user=request.user).aggregate(Sum("test_time"))["test_time__sum"] or 0
    hours       = total_typing_seconds // 3600
    minutes     = (total_typing_seconds % 3600) // 60
    seconds     = total_typing_seconds % 60
    time_typing = f"{hours:02}:{minutes:02}:{seconds:02}"

    return no_cache(render(request, "dashboard.html", {
        "results": recent_results, "total_tests": total_tests, "total_time": total_time,
        "selected_time": filter_time, "graph_labels": graph_labels, "graph_wpm": graph_wpm,
        "tests_completed": results.count(), "time_typing": time_typing,
    }))




# forgot password
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = request.build_absolute_uri(
            reverse("reset_password", kwargs={"uidb64": uid, "token": token})
         )

            send_mail(
                "Reset Password",
                f"Click link:\n{reset_link}",
                "settings.DEFAULT_FROM_EMAIL",
                [email],
            )

        except User.DoesNotExist:
            pass

        return JsonResponse({"status": "success"})

def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and default_token_generator.check_token(user, token):

        if request.method == "POST":
            password = request.POST.get("password")
            confirm = request.POST.get("confirm_password")

            if password == confirm:
                user.set_password(password)
                user.save()
                return redirect("login")

            return render(request, "password_flow.html", {
                "step": "reset",
                "error": "Passwords do not match"
            })

        return render(request, "password_flow.html", {"step": "reset"})

    else:
        return render(request, "activation_invalid.html")