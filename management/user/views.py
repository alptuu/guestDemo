from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from .forms import LoginForm, StyledPasswordChangeForm, UserCreateForm, UserUpdateForm
from .models import Profile
from .permissions import admin_required, get_profile

User = get_user_model()


class PanelLoginView(LoginView):
    template_name = "user/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class PanelPasswordChangeView(PasswordChangeView):
    template_name = "user/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("user:profile")

    def form_valid(self, form):
        messages.success(self.request, "Parolanız güncellendi.")
        return super().form_valid(form)


@login_required
def profile(request):
    from graph.models import GraphRun

    runs = GraphRun.objects.filter(user=request.user)
    return render(
        request,
        "user/profile.html",
        {
            "profile": get_profile(request.user),
            "run_count": runs.count(),
            "recent_runs": runs[:5],
        },
    )


@admin_required
def user_list(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    users = User.objects.order_by("username")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    if role in dict(Profile.ROLE_CHOICES):
        role_match = Q(profile__role=role)
        if role == Profile.ROLE_ADMIN:
            role_match |= Q(is_superuser=True)
        users = users.filter(role_match)
    page = Paginator(users, 15).get_page(request.GET.get("page"))
    for user in page:
        get_profile(user)
    admin_count = User.objects.filter(Q(profile__role=Profile.ROLE_ADMIN) | Q(is_superuser=True)).count()
    total_users = User.objects.count()
    return render(
        request,
        "user/user_list.html",
        {
            "page": page,
            "query": query,
            "role": role,
            "role_choices": Profile.ROLE_CHOICES,
            "total_users": total_users,
            "admin_count": admin_count,
            "personnel_count": total_users - admin_count,
        },
    )


@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"“{user.username}” kullanıcısı oluşturuldu.")
        return redirect("user:user_list")
    return render(request, "user/user_form.html", {"form": form, "title": "Yeni kullanıcı"})


@admin_required
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=target, editing_self=target.pk == request.user.pk)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"“{target.username}” kullanıcısı güncellendi.")
        return redirect("user:user_list")
    return render(
        request,
        "user/user_form.html",
        {"form": form, "title": f"Kullanıcıyı düzenle: {target.username}", "target": target},
    )


@admin_required
def user_set_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = AdminPasswordChangeForm(target, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"“{target.username}” için yeni parola belirlendi.")
        return redirect("user:user_list")
    return render(
        request,
        "user/user_form.html",
        {"form": form, "title": f"Parola sıfırla: {target.username}", "target": target, "is_password": True},
    )
