from django.urls import path
from users.views import RegisterView, LoginView, LogoutView, ProfileView, DeleteUserView, UserListView, EditUserProfileView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('users_list/', UserListView.as_view(), name='users_list'),
    path('edit_profile/', EditUserProfileView.as_view(), name='edit_profile'),
    path('delete_user/<int:user_id>/', DeleteUserView.as_view(), name='delete_user')
]
