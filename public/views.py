"""
Public API Views for api.runah.pt
"""

import re
import json
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class GiveawayView(APIView):
    """
    Public endpoint to get current giveaway information.
    Cached for 1 hour to protect against DDoS attacks.
    
    Returns: giveaway title, items, prices, images, and rules
    """
    
    CACHE_KEY = 'public_giveaway_data'
    
    def get(self, request):
        # Check cache first
        cached_data = cache.get(self.CACHE_KEY)
        if cached_data:
            cached_data['cached'] = True
            return Response(cached_data)
        
        try:
            config_path = settings.GIVEAWAY_CONFIG_PATH
            base_url = settings.GIVEAWAY_BASE_URL
            
            # Read and parse the JavaScript config file
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                return Response({
                    "success": False,
                    "error": "Giveaway configuration not found"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Parse the config using fallback regex parser
            config_data = self._parse_config(content)
            
            giveaway_data = config_data.get('giveaway', {})
            partnership_data = config_data.get('partnership', {})
            
            # Process prize images to include full URLs
            prizes = []
            for prize in giveaway_data.get('prizes', []):
                prizes.append({
                    "name": prize.get('name', ''),
                    "image": f"{base_url}/{prize.get('image', '')}",
                    "alt": prize.get('alt', prize.get('name', ''))
                })
            
            response_data = {
                "success": True,
                "cached": False,
                "cache_duration_seconds": settings.GIVEAWAY_CACHE_DURATION,
                "giveaway": {
                    "title": giveaway_data.get('title', ''),
                    "total_value": giveaway_data.get('totalValue', ''),
                    "prizes": prizes,
                    "rules": {
                        "minimum_deposit": giveaway_data.get('rules', {}).get('minimumDeposit', ''),
                        "bonus_code": giveaway_data.get('rules', {}).get('bonusCode', ''),
                        "additional_info": giveaway_data.get('rules', {}).get('additionalInfo', ''),
                        "valid_period": giveaway_data.get('rules', {}).get('validPeriod', '')
                    }
                },
                "partnership": {
                    "name": partnership_data.get('partnerName', ''),
                    "logo": f"{base_url}/{partnership_data.get('partnerLogo', '')}",
                    "url": partnership_data.get('partnerUrl', ''),
                    "bonus_code": partnership_data.get('bonusCode', ''),
                    "bonus_percentage": partnership_data.get('bonusPercentage', '')
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in cache
            cache.set(self.CACHE_KEY, response_data, settings.GIVEAWAY_CACHE_DURATION)
            
            return Response(response_data)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _parse_config(self, content):
        """
        Parse the giveaway config from JavaScript file.
        Uses regex patterns to extract values.
        """
        config = {
            'partnership': {},
            'giveaway': {
                'prizes': [],
                'rules': {}
            }
        }
        
        # Extract partnership values
        partner_patterns = {
            'partnerName': r'partnerName:\s*["\']([^"\']+)["\']',
            'partnerLogo': r'partnerLogo:\s*["\']([^"\']+)["\']',
            'partnerUrl': r'partnerUrl:\s*["\']([^"\']+)["\']',
            'bonusCode': r'bonusCode:\s*["\']([^"\']+)["\']',
            'bonusPercentage': r'bonusPercentage:\s*["\']([^"\']+)["\']'
        }
        
        for key, pattern in partner_patterns.items():
            match = re.search(pattern, content)
            if match:
                config['partnership'][key] = match.group(1)
        
        # Extract giveaway values
        title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)
        if title_match:
            config['giveaway']['title'] = title_match.group(1)
        
        total_match = re.search(r'totalValue:\s*["\']([^"\']+)["\']', content)
        if total_match:
            config['giveaway']['totalValue'] = total_match.group(1)
        
        # Extract prizes - find all prize objects
        prizes_section = re.search(r'prizes:\s*\[([\s\S]*?)\]', content)
        if prizes_section:
            prize_content = prizes_section.group(1)
            
            # Remove commented lines (lines starting with //)
            prize_content_clean = '\n'.join(
                line for line in prize_content.split('\n') 
                if not line.strip().startswith('//')
            )
            
            # Find all prize objects - handle any property order
            prize_objects = re.findall(r'\{[^}]+\}', prize_content_clean)
            for prize_obj in prize_objects:
                name_match = re.search(r'name:\s*["\']([^"\']+)["\']', prize_obj)
                image_match = re.search(r'image:\s*["\']([^"\']+)["\']', prize_obj)
                alt_match = re.search(r'alt:\s*["\']([^"\']+)["\']', prize_obj)
                
                if name_match and image_match:
                    config['giveaway']['prizes'].append({
                        'name': name_match.group(1),
                        'image': image_match.group(1),
                        'alt': alt_match.group(1) if alt_match else name_match.group(1)
                    })
        
        # Extract rules
        rules_patterns = {
            'minimumDeposit': r'minimumDeposit:\s*["\']([^"\']+)["\']',
            'bonusCode': r'rules:\s*\{[^}]*bonusCode:\s*["\']([^"\']+)["\']',
            'additionalInfo': r'additionalInfo:\s*["\']([^"\']+)["\']',
            'validPeriod': r'validPeriod:\s*["\']([^"\']+)["\']'
        }
        
        for key, pattern in rules_patterns.items():
            match = re.search(pattern, content)
            if match:
                config['giveaway']['rules'][key] = match.group(1)
        
        return config


class HealthView(APIView):
    """Health check endpoint"""
    
    def get(self, request):
        return Response({
            "status": "healthy",
            "service": "api.runah.pt",
            "timestamp": datetime.now().isoformat()
        })
