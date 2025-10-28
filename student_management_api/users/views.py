from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.exceptions import TokenError
from users.serializers import UserRegistrationSerializer, UserProfileSerializer
from users.models import ActiveSession
from datetime import timedelta

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data or {}
        required = ['username', 'first_name', 'last_name', 'email', 'phone', 'password']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return Response({'error': 'Missing required fields', 'missing_fields': missing},status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=data.get('username')).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=data.get('email')).exists():
            return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = UserRegistrationSerializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                user_data = UserProfileSerializer(user).data
                return Response({'message': 'User registered successfully', 'user': user_data}, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Validation failed', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Error during registration', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data or {}
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            now = timezone.now()
            expired_sessions = ActiveSession.objects.filter(expires_at__lt=now, active=True)
            for s in expired_sessions:
                s.active = False
                s.save()
            active_any = ActiveSession.objects.filter(active=True).first()
            if active_any:
                return Response({'error': 'Another user is already logged in. Please wait until they logout.'},
                                status=status.HTTP_403_FORBIDDEN)
            user = authenticate(username=username, password=password)
            if not user:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh_str = str(refresh)
            expires_at = timezone.now() + refresh.access_token.lifetime
            ActiveSession.objects.create(
                user=user,
                refresh_token=refresh_str,
                access_token=access,
                expires_at=expires_at,
                active=True
            )
            return Response(
                {'access': access, 'refresh': refresh_str, 'message': 'Login successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Server error during login', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            session = ActiveSession.objects.filter(user=request.user, active=True).first()
            if not session:
                return Response({'error': 'No active session found for this user'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                refresh_token = RefreshToken(session.refresh_token)
                refresh_token.blacklist()
            except TokenError:
                pass
            try:
                if session.access_token:
                    token_obj = OutstandingToken.objects.filter(token=session.access_token).first()
                    if token_obj:
                        BlacklistedToken.objects.get_or_create(token=token_obj)
            except Exception:
                pass
            session.active = False
            session.save()
            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Server error during logout', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Could not fetch profile', 'details': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, user_id):
        try:
            current_user = request.user
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            if current_user.role == 'admin':
                if current_user.id == target_user.id:
                    return Response({'error': 'Admins cannot delete themselves'}, status=status.HTTP_400_BAD_REQUEST)
                target_user.delete()
                return Response({'message': f'User {target_user.username} deleted successfully by admin.'}, status=status.HTTP_200_OK)
            elif current_user.role == 'teacher':
                if target_user.role == 'student':
                    target_user.delete()
                    return Response({'message': f'Student {target_user.username} deleted successfully by teacher.'}, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'Teachers can only delete students.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': 'You do not have permission to delete users.'}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'error': 'Error deleting user', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class UserListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            current_user = request.user
            if current_user.role == 'admin':
                users = User.objects.all()
            elif current_user.role == 'teacher':
                users = User.objects.filter(role='student')
            else:
                return Response({"error": "You do not have permission to view users list."},status=status.HTTP_403_FORBIDDEN)
            serializer = UserProfileSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Failed to fetch users list", "details": str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class EditUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        try:
            user = request.user
            editable_fields = ['first_name', 'last_name', 'email', 'phone']
            for field in editable_fields:
                if field in request.data:
                    setattr(user, field, request.data[field])
            user.save()
            serializer = UserProfileSerializer(user)
            return Response({"message": "Profile updated successfully", "user": serializer.data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Error updating profile", "details": str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)