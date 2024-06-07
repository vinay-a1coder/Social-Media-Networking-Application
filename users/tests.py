
# Create your tests here.
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from .models import FriendRequest
from .serializers import FriendRequestSerializer, UserSerializer
from users.models import User


class TestFriendFunctions(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(name='user1', email='user1@example.com', password='testpassword')
        self.user2 = User.objects.create_user(name='user2', email='user2@example.com', password='testpassword')
        self.user3 = User.objects.create_user(name='user3', email='user3@example.com', password='testpassword')

    def test_send_friend_request(self):
        response = self.client.post('/send_friend_request/', {'receiver_email': self.user2.email}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        
        response = self.client.post('/send_friend_request/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        
        response = self.client.post('/send_friend_request/', {'receiver_email': 'nonexistent@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        
        for _ in range(4):
            self.client.post('/send_friend_request/', {'receiver_email': self.user3.email}, format='json')
        response = self.client.post('/send_friend_request/', {'receiver_email': self.user3.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_friend_request(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        response = self.client.put(f'/accept_friend_request/{friend_request.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        
        response = self.client.put('/accept_friend_request/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_friend_request(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        response = self.client.put(f'/reject_friend_request/{friend_request.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        
        response = self.client.put('/reject_friend_request/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_friends(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2, is_accepted=True)
        response = self.client.get('/list_friends/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_pending_requests(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        response = self.client.get('/list_pending_requests/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
