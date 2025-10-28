"""
WAF Test API Views
Contains various endpoints to test WAF functionality:
- Secure endpoints (protected by proper validation)
- Vulnerable endpoints (for testing WAF protection)
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response
import json


@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'WAF Test Backend',
        'version': '1.0.0'
    })


@api_view(['GET', 'POST'])
def secure_endpoint(request):
    """
    Secure endpoint with proper validation
    This should pass through WAF without issues
    """
    if request.method == 'GET':
        return Response({
            'message': 'This is a secure GET endpoint',
            'data': {
                'user': 'test_user',
                'timestamp': '2025-10-28'
            }
        })
    else:
        # POST with proper validation
        try:
            data = request.data
            # Proper input validation
            if 'name' in data and isinstance(data['name'], str):
                if len(data['name']) > 100:
                    return Response({'error': 'Name too long'}, status=400)
                
                return Response({
                    'message': 'Data received securely',
                    'received': data
                })
            else:
                return Response({'error': 'Invalid input'}, status=400)
        except Exception as e:
            return Response({'error': 'Bad request'}, status=400)


@csrf_exempt
@api_view(['GET'])
def vulnerable_sql_injection(request):
    """
    VULNERABLE: SQL Injection endpoint
    DO NOT USE IN PRODUCTION - FOR WAF TESTING ONLY
    
    Test with: ?id=1' OR '1'='1
    """
    user_id = request.GET.get('id', '1')
    
    # VULNERABLE: Direct SQL query without parameterization
    # WAF should block this if malicious input is detected
    try:
        with connection.cursor() as cursor:
            # This is intentionally vulnerable for testing
            query = f"SELECT * FROM auth_user WHERE id = {user_id}"
            cursor.execute(query)
            results = cursor.fetchall()
            
        return JsonResponse({
            'message': 'Query executed',
            'query': query,
            'note': 'This endpoint is vulnerable to SQL injection - WAF should protect it'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'note': 'Exception occurred - possibly blocked or invalid query'
        }, status=400)


@csrf_exempt
@api_view(['POST'])
def vulnerable_xss(request):
    """
    VULNERABLE: XSS endpoint
    DO NOT USE IN PRODUCTION - FOR WAF TESTING ONLY
    
    Test with: {"comment": "<script>alert('XSS')</script>"}
    """
    try:
        data = request.data
        comment = data.get('comment', '')
        
        # VULNERABLE: No sanitization of user input
        # WAF should detect and block XSS attempts
        return JsonResponse({
            'message': 'Comment received',
            'comment': comment,  # This would reflect the XSS payload
            'note': 'This endpoint is vulnerable to XSS - WAF should protect it'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['POST'])
def vulnerable_command_injection(request):
    """
    VULNERABLE: Command Injection endpoint
    DO NOT USE IN PRODUCTION - FOR WAF TESTING ONLY
    
    Test with: {"filename": "test.txt; ls -la"}
    """
    try:
        data = request.data
        filename = data.get('filename', 'default.txt')
        
        # VULNERABLE: No validation of user input
        # WAF should detect command injection attempts
        return JsonResponse({
            'message': 'Would process file',
            'filename': filename,
            'note': 'This endpoint is vulnerable to command injection - WAF should protect it',
            'warning': 'Command execution disabled for safety'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def test_file_inclusion(request):
    """
    VULNERABLE: Local File Inclusion test
    DO NOT USE IN PRODUCTION - FOR WAF TESTING ONLY
    
    Test with: ?file=../../../../etc/passwd
    """
    filepath = request.GET.get('file', 'default.txt')
    
    return JsonResponse({
        'message': 'File access attempted',
        'file': filepath,
        'note': 'This endpoint is vulnerable to LFI - WAF should protect it',
        'warning': 'Actual file reading disabled for safety'
    })


@api_view(['POST'])
def rate_limit_test(request):
    """
    Endpoint to test rate limiting
    Make multiple rapid requests to trigger rate limiting
    """
    return Response({
        'message': 'Request processed',
        'note': 'Make many rapid requests to test WAF rate limiting'
    })


@api_view(['GET'])
def large_response_test(request):
    """
    Test WAF handling of large responses
    """
    large_data = {
        'items': [{'id': i, 'data': 'x' * 100} for i in range(100)]
    }
    return Response({
        'message': 'Large response test',
        'data': large_data
    })


@api_view(['GET'])
def waf_test_suite(request):
    """
    Returns information about all available test endpoints
    """
    endpoints = {
        'secure_endpoints': [
            {
                'path': '/api/health/',
                'method': 'GET',
                'description': 'Health check endpoint'
            },
            {
                'path': '/api/secure/',
                'method': 'GET/POST',
                'description': 'Properly secured endpoint with validation'
            }
        ],
        'vulnerable_endpoints': [
            {
                'path': '/api/test/sql-injection/',
                'method': 'GET',
                'description': 'SQL injection test',
                'test_payload': '?id=1\' OR \'1\'=\'1'
            },
            {
                'path': '/api/test/xss/',
                'method': 'POST',
                'description': 'XSS test',
                'test_payload': '{"comment": "<script>alert(\'XSS\')</script>"}'
            },
            {
                'path': '/api/test/command-injection/',
                'method': 'POST',
                'description': 'Command injection test',
                'test_payload': '{"filename": "test.txt; ls -la"}'
            },
            {
                'path': '/api/test/file-inclusion/',
                'method': 'GET',
                'description': 'File inclusion test',
                'test_payload': '?file=../../../../etc/passwd'
            }
        ],
        'performance_tests': [
            {
                'path': '/api/test/rate-limit/',
                'method': 'POST',
                'description': 'Rate limiting test - make rapid requests'
            },
            {
                'path': '/api/test/large-response/',
                'method': 'GET',
                'description': 'Large response handling test'
            }
        ],
        'note': 'WAF should block malicious payloads to vulnerable endpoints'
    }
    
    return Response(endpoints)
