from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny]) # anyone can register, no token needed
@csrf_exempt
def register(request):
    """
    POST /auth/register
    Body: { username, email, password, password2, role }
    Returns: user info + tokens
    """
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens for the new user immediately
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'User created successfully!',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),  # short lived (1 hour)
                'refresh': str(refresh),               # long lived (7 days)
            }
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny]) # anyone can login, no token needed
@csrf_exempt
def login(request):
    """
    POST /auth/login
    Body: { username, password }
    Returns: user info + tokens
    """
    username = request.data.get('username')
    password = request.data.get('password')

    # Check username and password exist in request
    if not username or not password:
        return Response(
            {'error': 'Please provide username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # authenticate() checks username+password against database
    user = authenticate(username=username, password=password)

    if user:
        # Generate new tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful!',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)

    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated]) # MUST have valid token
def verify_token(request):
    """
    GET /auth/verify
    Header: Authorization: Bearer <token>
    Returns: user info if token is valid
    """
    return Response({
        'message': 'Token is valid!',
        'user': UserSerializer(request.user).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    POST /auth/logout
    Blacklists the refresh token
    """
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {'message': 'Logged out successfully!'},
            status=status.HTTP_200_OK
        )
    except Exception:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )
