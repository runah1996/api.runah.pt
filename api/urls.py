"""
API URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    # Health and info
    path('health/', views.health_check, name='health_check'),
    path('test-suite/', views.waf_test_suite, name='test_suite'),
    
    # Secure endpoints
    path('secure/', views.secure_endpoint, name='secure_endpoint'),
    
    # Vulnerable endpoints for WAF testing
    path('test/sql-injection/', views.vulnerable_sql_injection, name='sql_injection_test'),
    path('test/xss/', views.vulnerable_xss, name='xss_test'),
    path('test/command-injection/', views.vulnerable_command_injection, name='command_injection_test'),
    path('test/file-inclusion/', views.test_file_inclusion, name='file_inclusion_test'),
    
    # Performance tests
    path('test/rate-limit/', views.rate_limit_test, name='rate_limit_test'),
    path('test/large-response/', views.large_response_test, name='large_response_test'),
]

