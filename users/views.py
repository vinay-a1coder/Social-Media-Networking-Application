from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, FriendRequestSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from datetime import datetime, timedelta
from rest_framework.permissions import IsAuthenticated
from .models import FriendRequest
from django.utils import timezone


User = get_user_model()

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    Registers a new user with the provided email, name and password.

    Parameters:
    email (str)   : The email of the new user.
    name (str)    : The username of the new user.
    password (str): The password of the new user.

    Returns:
    Response: An HTTP response containing either the serialized data of the registered user with status 201 (HTTP_CREATED)
    if the registration was successful, or the errors encountered during serialization/validation with status 400 (HTTP_BAD_REQUEST)
    if the registration failed
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """
    Authenticates a user based on the provided email and password.

    Parameters:
    request (HttpRequest): The HTTP request containing user login data.

    Returns:
    Response: An HTTP response containing a pair of JWT tokens (refresh token and access token)
    if the login was successful, along with status 200 (HTTP_OK). If the login credentials were invalid,
    it returns a response with status 401 (HTTP_UNAUTHORIZED) and a message indicating the invalid credentials.
    If there are errors in the provided data, it returns a response with status 400 (HTTP_BAD_REQUEST) and
    a dictionary of serializer errors.
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(email=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retrieves a queryset of users based on the provided search keyword.

        This method filters the queryset of users based on the 'search' query parameter
        present in the request. It performs a case-insensitive search on the 'email' and 'name'
        fields of the User model. If a search keyword is provided, it returns a filtered queryset
        containing users whose email or name matches the keyword. If no keyword is provided or the
        keyword does not match any users, an empty queryset is returned.

        Returns:
        queryset: A queryset of users filtered based on the search keyword provided in the request.
        """
        keyword = self.request.query_params.get('search', None)
        if keyword:
            return User.objects.filter(
                Q(email__iexact=keyword) | 
                Q(name__icontains=keyword)
            )
        return User.objects.none()
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request):
    """
    Sends a friend request from the current user to another user based on the provided receiver email.

    Parameters:
    request (HttpRequest): The HTTP request containing data about the friend request.

    Returns:
    Response: An HTTP response indicating the outcome of the friend request. If the receiver email is not provided
    in the request data, it returns a response with status 400 (HTTP_BAD_REQUEST) and a message indicating that
    the receiver email is required. If the receiver user does not exist, it returns a response with status 404
    (HTTP_NOT_FOUND) and a message indicating that the user was not found. If a friend request has already been
    sent to the receiver user by the current user, it returns a response with status 400 (HTTP_BAD_REQUEST) and
    a message indicating that a friend request has already been sent. If the current user has sent more than
    3 friend requests in the last minute, it returns a response with status 429 (HTTP_TOO_MANY_REQUESTS) and
    a message indicating that the user has exceeded the maximum limit for friend requests. If the friend request
    is successfully created, it returns a response with status 201 (HTTP_CREATED) and the serialized data of
    the created friend request.
    """
    receiver_email = request.data.get('receiver_email')
    if not receiver_email:
        return Response({"detail": "Receiver email is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        receiver = User.objects.get(email=receiver_email)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if FriendRequest.objects.filter(sender=request.user, receiver=receiver).exists():
        return Response({"detail": "Friend request already sent"}, status=status.HTTP_400_BAD_REQUEST)

    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_requests = FriendRequest.objects.filter(sender=request.user, timestamp__gte=one_minute_ago)
    if recent_requests.count() >= 3:
        return Response({"detail": "You can send a maximum of 3 friend requests per minute"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    friend_request = FriendRequest(sender=request.user, receiver=receiver)
    friend_request.save()
    return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friend_request(request, pk):
    """
    Accepts a friend request sent to the current user.

    Parameters:
    request (HttpRequest): The HTTP request containing data about the friend request acceptance.
    pk (int): The primary key of the friend request to be accepted.

    Returns:
    Response: An HTTP response indicating the outcome of accepting the friend request. If the friend request
    with the specified primary key and receiver user does not exist, it returns a response with status 404
    (HTTP_NOT_FOUND) and a message indicating that the friend request was not found. If the friend request
    is successfully accepted, it updates the 'is_accepted' field of the friend request to True, saves the
    changes, and returns a response with the serialized data of the updated friend request.
    """
    try:
        friend_request = FriendRequest.objects.get(pk=pk, receiver=request.user)
    except FriendRequest.DoesNotExist:
        return Response({"detail": "Friend request not found"}, status=status.HTTP_404_NOT_FOUND)

    friend_request.is_accepted = True
    friend_request.save()
    return Response(FriendRequestSerializer(friend_request).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_friend_request(request, pk):
    """
    Rejects a friend request sent to the current user.

    Parameters:
    request (HttpRequest): The HTTP request containing data about the friend request rejection.
    pk (int): The primary key of the friend request to be rejected.

    Returns:
    Response: An HTTP response indicating the outcome of rejecting the friend request. If the friend request
    with the specified primary key and receiver user does not exist, it returns a response with status 404
    (HTTP_NOT_FOUND) and a message indicating that the friend request was not found. If the friend request
    is successfully rejected, it updates the 'is_rejected' field of the friend request to True, saves the
    changes, and returns a response with the serialized data of the updated friend request.
    """
    try:
        friend_request = FriendRequest.objects.get(pk=pk, receiver=request.user)
    except FriendRequest.DoesNotExist:
        return Response({"detail": "Friend request not found"}, status=status.HTTP_404_NOT_FOUND)

    friend_request.is_rejected = True
    friend_request.save()
    return Response(FriendRequestSerializer(friend_request).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_friends(request):
    """
    Retrieves a list of friends for the current user.

    Parameters:
    request (HttpRequest): The HTTP request to list the friends.

    Returns:
    Response: An HTTP response containing the serialized data of the friends of the current user.
    The response includes users who have either sent or received friend requests that have been accepted
    by both parties. If there are no friends found, an empty list is returned. The response is serialized
    using the UserSerializer and returned with status 200 (HTTP_OK).
    """
    friends = User.objects.filter(
        Q(sent_requests__receiver=request.user, sent_requests__is_accepted=True) |
        Q(received_requests__sender=request.user, received_requests__is_accepted=True)
    ).distinct()
    return Response(UserSerializer(friends, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_requests(request):
    """
    Retrieves a list of pending friend requests for the current user.

    Parameters:
    request (HttpRequest): The HTTP request to list the pending friend requests.

    Returns:
    Response: An HTTP response containing the serialized data of the pending friend requests
    received by the current user. The response includes friend requests that have been sent to
    the user but have not yet been accepted or rejected. If there are no pending requests found,
    an empty list is returned. The response is serialized using the FriendRequestSerializer and
    returned with status 200 (HTTP_OK).
    """
    pending_requests = FriendRequest.objects.filter(receiver=request.user, is_accepted=False, is_rejected=False)
    return Response(FriendRequestSerializer(pending_requests, many=True).data)
