from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import requests
from django.conf import settings
from .models import UserProfile, DetectionHistory
from .serializers import UserProfileSerializer, DetectionHistorySerializer


def get_user_from_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        print(f"Missing or invalid auth header: {auth_header}")
        return None
    token = auth_header.split(' ')[1]
    try:
        response = requests.get(
            f"{settings.AUTH_SERVICE_URL}/auth/verify/",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get('user')
        print(f"Auth service returned {response.status_code}: {response.text}")
        return None
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None



def get_or_create_profile(user_data):
    profile, created = UserProfile.objects.get_or_create(
        user_id=user_data['id'],
        defaults={
            'username': user_data['username'],
            'email': user_data['email'],
            'role': user_data.get('role', 'user'),
        }
    )
    return profile


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def my_profile(request):
    user_data = get_user_from_token(request)
    if not user_data:
        return Response(
            {'error': 'Invalid or missing token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    profile = get_or_create_profile(user_data)
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == 'PUT':
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def detection_history(request):
    user_data = get_user_from_token(request)
    if not user_data:
        return Response(
            {'error': 'Invalid or missing token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    profile = get_or_create_profile(user_data)
    if request.method == 'GET':
        detections = DetectionHistory.objects.filter(
            user_profile=profile
        ).order_by('-created_at')
        serializer = DetectionHistorySerializer(detections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == 'POST':
        serializer = DetectionHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_profile=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def detection_detail(request, pk):
    user_data = get_user_from_token(request)
    if not user_data:
        return Response(
            {'error': 'Invalid or missing token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    profile = get_or_create_profile(user_data)
    try:
        detection = DetectionHistory.objects.get(pk=pk, user_profile=profile)
        serializer = DetectionHistorySerializer(detection)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except DetectionHistory.DoesNotExist:
        return Response(
            {'error': 'Detection not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def detect_image(request):
    """
    Proxy vers ai-service : vérifie le JWT, envoie l'image, enregistre l'historique.
    Réponse : prediction, confidence, label, history_id, username.
    """
    user_data = get_user_from_token(request)
    if not user_data:
        return Response(
            {'error': 'Invalid or missing token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    profile = get_or_create_profile(user_data)

    if 'file' not in request.FILES:
        print("Image received: None (request.FILES missing 'file')")
        return Response(
            {'error': 'No image file provided. Use form field name "file".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    upload = request.FILES['file']
    print("Image received:", request.FILES)
    print(
        f"Detect request file name={upload.name} size={upload.size} content_type={upload.content_type}"
    )
    max_bytes = getattr(settings, 'DETECT_MAX_UPLOAD_BYTES', 10 * 1024 * 1024)
    if upload.size > max_bytes:
        return Response(
            {'error': f'File too large (max {max_bytes // (1024 * 1024)} MB).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    content_type = upload.content_type or ''
    if content_type and not content_type.startswith('image/'):
        return Response(
            {'error': 'Invalid file type. Please upload an image (e.g. JPEG, PNG, WebP).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    auth_header = request.headers.get('Authorization', '')
    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/detect-fake"
    upload.seek(0)
    files = {
        'file': (
            upload.name or 'image.jpg',
            upload.read(),
            content_type or 'application/octet-stream',
        ),
    }
    try:
        print(f"Forwarding image to AI service: {url}")
        ai_resp = requests.post(
            url,
            files=files,
            headers={'Authorization': auth_header},
            timeout=120,
        )
        print(f"AI response status: {ai_resp.status_code}")
    except requests.RequestException as exc:
        print(f"AI request error: {exc}")
        return Response(
            {'error': 'AI service unavailable', 'detail': str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    try:
        payload = ai_resp.json()
        print("AI response payload:", payload)
    except ValueError:
        print("AI response JSON decode failed")
        return Response(
            {'error': 'Invalid response from AI service'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if ai_resp.status_code == 401:
        return Response(
            payload if isinstance(payload, dict) else {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if ai_resp.status_code == 400:
        return Response(
            payload if isinstance(payload, dict) else {'error': 'Bad request'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if ai_resp.status_code == 503:
        detail = payload.get('detail') if isinstance(payload, dict) else 'Model is loading'
        return Response(
            {'error': 'AI model not ready', 'detail': detail},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if ai_resp.status_code != 200:
        detail = payload.get('detail') if isinstance(payload, dict) else str(payload)
        return Response(
            {'error': 'Detection failed', 'detail': detail},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    prediction = payload.get('prediction') or payload.get('result')
    confidence = payload.get('confidence')
    real_prob = payload.get('real_prob')
    fake_prob = payload.get('fake_prob')
    label = (payload.get('label') or '')[:512]
    ensemble_details = payload.get('ensemble_details')

    if prediction not in ('real', 'fake'):
        return Response(
            {'error': 'Invalid prediction from AI service'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return Response(
            {'error': 'Invalid confidence from AI service'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    row = DetectionHistory.objects.create(
        user_profile=profile,
        image_name=(upload.name or 'image')[:255],
        result=prediction,
        confidence=confidence,
        label=label,
    )

    response_payload = {
        'prediction': prediction,
        'confidence': confidence,
        'label': label or None,
        'username': profile.username,
        'history_id': row.id,
    }

    if real_prob is not None:
        response_payload['real_prob'] = real_prob
    if fake_prob is not None:
        response_payload['fake_prob'] = fake_prob
    if isinstance(ensemble_details, dict):
        response_payload['ensemble_details'] = ensemble_details

    return Response(response_payload, status=status.HTTP_200_OK)
