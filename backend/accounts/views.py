from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer

@api_view(['POST'])
def register_user(request):
    # 1. Pass the incoming JSON data to our Translator/Bouncer
    serializer = UserRegistrationSerializer(data=request.data)
    
    # 2. If the data follows all our rules (valid email, max length, etc.)
    if serializer.is_valid():
        serializer.save() # Saves to PostgreSQL securely
        return Response({"message": "User created successfully!"}, status=status.HTTP_201_CREATED)
    
    # 3. If something is wrong, send the exact errors back to the frontend
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)