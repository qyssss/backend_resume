from django.db import models

# Create your models here.
class FirebaseUser:
    def __init__(self, email, username, password):
        self.email = email
        self.username = username
        self.password = password

    @staticmethod
    def from_dict(source):
        return FirebaseUser(
            email=source.get('email'),
            username=source.get('username'),
            password=source.get('password')
        )