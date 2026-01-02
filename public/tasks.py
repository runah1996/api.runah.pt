"""
Celery tasks for CSGO.NET case data caching
"""

import json
import hashlib
import logging
from decimal import Decimal
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

import websocket

from .models import Case, CaseItem, CaseHistory

logger = logging.getLogger(__name__)


class CSGONetWebSocketClient:
    """
    Client for connecting to CSGO.NET WebSocket and collecting case data.
    Uses Meteor/DDP protocol.
    """
    
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.cases = {}
        self.case_ranges = {}
        self.connected = False
        self.ws = None
        
    def connect_and_collect(self):
        """Connect to WebSocket and collect all case data."""
        url = settings.CSGONET_WEBSOCKET_URL
        
        try:
            self.ws = websocket.create_connection(
                url,
                timeout=self.timeout,
                header={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Origin': 'https://csgo.net'
                }
            )
            
            # Send DDP connect message
            connect_msg = json.dumps({
                "msg": "connect",
                "version": "1",
                "support": ["1", "pre2", "pre1"]
            })
            self.ws.send(connect_msg)
            
            # Subscribe to cases
            sub_cases = json.dumps({
                "msg": "sub",
                "id": "cases-sub",
                "name": "cases",
                "params": []
            })
            self.ws.send(sub_cases)
            
            # Subscribe to case ranges (odds/items)
            sub_ranges = json.dumps({
                "msg": "sub",
                "id": "ranges-sub",
                "name": "pf_case_ranges",
                "params": []
            })
            self.ws.send(sub_ranges)
            
            # Collect messages until we have all data
            cases_ready = False
            ranges_ready = False
            message_count = 0
            max_messages = 5000  # Increased limit for more data
            no_data_count = 0
            max_no_data = 3  # Exit after 3 consecutive timeouts
            
            while message_count < max_messages:
                try:
                    msg = self.ws.recv()
                    if not msg:
                        no_data_count += 1
                        if no_data_count >= max_no_data:
                            break
                        continue
                        
                    no_data_count = 0  # Reset on successful receive
                    data = json.loads(msg)
                    msg_type = data.get("msg")
                    
                    if msg_type == "connected":
                        self.connected = True
                        logger.info("Connected to CSGO.NET WebSocket")
                        
                    elif msg_type == "added":
                        collection = data.get("collection")
                        doc_id = data.get("id")
                        fields = data.get("fields", {})
                        
                        if collection == "cases":
                            self.cases[doc_id] = {
                                "id": doc_id,
                                **fields
                            }
                            
                        elif collection == "pf_case_ranges":
                            case_id = fields.get("caseID")
                            if case_id:
                                self.case_ranges[case_id] = fields.get("items", [])
                                
                    elif msg_type == "ready":
                        subs = data.get("subs", [])
                        if "cases-sub" in subs:
                            cases_ready = True
                            logger.info(f"Cases ready: {len(self.cases)} cases")
                        if "ranges-sub" in subs:
                            ranges_ready = True
                            logger.info(f"Ranges ready: {len(self.case_ranges)} case ranges")
                            
                        # Exit when both are ready
                        if cases_ready and ranges_ready:
                            logger.info("Both subscriptions ready, finishing collection")
                            break
                            
                    elif msg_type == "ping":
                        self.ws.send(json.dumps({"msg": "pong"}))
                        
                    elif msg_type == "nosub":
                        # Subscription failed
                        sub_id = data.get("id")
                        logger.warning(f"Subscription failed: {sub_id}")
                        if sub_id == "ranges-sub":
                            ranges_ready = True  # Mark as ready even if failed
                        
                    message_count += 1
                    
                except websocket.WebSocketTimeoutException:
                    no_data_count += 1
                    if no_data_count >= max_no_data:
                        logger.warning("WebSocket timeout, finishing collection")
                        break
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise
        finally:
            if self.ws:
                self.ws.close()
        
        logger.info(f"Collection complete: {len(self.cases)} cases, {len(self.case_ranges)} ranges")
        return self._merge_data()
    
    def _merge_data(self):
        """Merge cases with their item ranges."""
        merged_cases = []
        
        # Total range is 10,000,000 (1 to 10000000)
        TOTAL_RANGE = 10_000_000
        
        for case_id, case_data in self.cases.items():
            items = self.case_ranges.get(case_id, [])
            
            processed_items = []
            for item in items:
                # Range is a list [start, end], probability % = ((end - start + 1) / 10,000,000) * 100
                item_range = item.get("range", [0, 0])
                if isinstance(item_range, list) and len(item_range) == 2:
                    range_size = item_range[1] - item_range[0] + 1
                    probability = (range_size / TOTAL_RANGE) * 100  # Convert to percentage
                else:
                    # Fallback to prob field if range is not available
                    probability = (item.get("prob", 0)) * 100  # Convert to percentage
                
                processed_items.append({
                    "id": item.get("name", "").split(" (")[0],  # Extract base name as ID
                    "name": item.get("name", ""),
                    "probability": probability,
                    "range": item_range,  # Keep original range for reference
                    "price_rub": item.get("price", 0),
                    "price_usd": item.get("price_usd"),
                    "price_eur": item.get("price_eur"),
                })
            
            merged_case = {
                "id": case_id,
                "name": case_data.get("name", ""),
                "image": case_data.get("image", ""),
                "price_rub": case_data.get("price", 0),
                "price_usd": case_data.get("price_usd"),
                "price_eur": case_data.get("price_eur"),
                "is_mining_case": case_data.get("isMiningCase", False),
                "items": processed_items
            }
            
            merged_cases.append(merged_case)
            
        return merged_cases


def calculate_expected_return(case_data):
    """Calculate expected return percentage for a case using USD prices."""
    items = case_data.get("items", [])
    case_price = case_data.get("price_usd", 0)
    
    if not items or not case_price or case_price <= 0:
        return None
    
    # Probability is now in percentage form (0-100), so divide by 100
    expected_value = sum(
        (item.get("price_usd") or 0) * ((item.get("probability") or 0) / 100)
        for item in items
    )
    
    return round((expected_value / case_price) * 100, 2)


def calculate_volatility(case_data):
    """
    Calculate volatility metrics for a case (High Risk / High Reward).
    
    Returns a dict with:
    - volatility: Coefficient of variation (std_dev / expected_value) - higher = more volatile
    - risk_level: 'low', 'medium', or 'high'
    - max_multiplier: Best possible return (max item price / case price)
    
    A case with same RTP but higher volatility means:
    - More "high risk / high reward" - rare expensive items, many cheap items
    - Lower volatility = more predictable outcomes around the expected value
    """
    import math
    
    items = case_data.get("items", [])
    case_price = case_data.get("price_usd", 0)
    
    if not items or not case_price or case_price <= 0:
        return None
    
    # Calculate expected value (mean return)
    expected_value = sum(
        (item.get("price_usd") or 0) * ((item.get("probability") or 0) / 100)
        for item in items
    )
    
    if expected_value <= 0:
        return None
    
    # Calculate variance: E[(X - μ)²] = Σ p_i * (x_i - μ)²
    variance = sum(
        ((item.get("probability") or 0) / 100) * ((item.get("price_usd") or 0) - expected_value) ** 2
        for item in items
    )
    
    # Standard deviation
    std_dev = math.sqrt(variance)
    
    # Coefficient of Variation (CV) = std_dev / mean
    # Higher CV = more volatile / risky
    cv = (std_dev / expected_value) if expected_value > 0 else 0
    
    # Find max possible return multiplier
    max_item_price = max((item.get("price_usd") or 0) for item in items)
    max_multiplier = round(max_item_price / case_price, 2) if case_price > 0 else 0
    
    # Classify risk level based on coefficient of variation
    # Thresholds based on real CSGO.NET data distribution:
    # - Median CV is ~1.45, 75th percentile is ~3.15
    # - Mining cases with huge jackpots have CV 20-35
    if cv < 1.5:
        risk_level = 'low'      # ~50% of cases - predictable outcomes
    elif cv < 4.0:
        risk_level = 'medium'   # ~40% of cases - moderate variance
    else:
        risk_level = 'high'     # ~10% of cases - mining/jackpot cases with extreme variance
    
    return {
        'volatility': round(cv, 4),
        'risk_level': risk_level,
        'max_multiplier': max_multiplier
    }


def hash_items(items_queryset):
    """Create a hash of item data for comparison."""
    items_data = [
        f"{item.item_id}:{item.probability}:{item.price_rub}"
        for item in items_queryset.order_by('item_id')
    ]
    return hashlib.md5("|".join(items_data).encode()).hexdigest()


def hash_items_data(items_list):
    """Create a hash of item data from raw data for comparison."""
    items_data = [
        f"{item.get('id', '')}:{item.get('probability', 0)}:{item.get('price_rub', 0)}"
        for item in sorted(items_list, key=lambda x: x.get('id', ''))
    ]
    return hashlib.md5("|".join(items_data).encode()).hexdigest()


def save_case_if_changed(case_data):
    """
    Save case to database only if data has changed.
    Returns True if changes were detected and saved.
    """
    case_id = case_data["id"]
    
    try:
        existing = Case.objects.prefetch_related('items').get(case_id=case_id)
        changes = []
        
        # Check for price changes
        new_price_rub = Decimal(str(case_data.get("price_rub", 0)))
        if existing.price_rub != new_price_rub:
            changes.append(("price_rub", str(existing.price_rub), str(new_price_rub)))
            
        new_price_usd = Decimal(str(case_data.get("price_usd", 0))) if case_data.get("price_usd") else None
        if existing.price_usd != new_price_usd:
            changes.append(("price_usd", str(existing.price_usd), str(new_price_usd)))
            
        new_price_eur = Decimal(str(case_data.get("price_eur", 0))) if case_data.get("price_eur") else None
        if existing.price_eur != new_price_eur:
            changes.append(("price_eur", str(existing.price_eur), str(new_price_eur)))
        
        new_expected_return = Decimal(str(case_data.get("expected_return", 0))) if case_data.get("expected_return") else None
        if existing.expected_return != new_expected_return:
            changes.append(("expected_return", str(existing.expected_return), str(new_expected_return)))
        
        # Check volatility changes
        new_volatility = Decimal(str(case_data.get("volatility", 0))) if case_data.get("volatility") else None
        if existing.volatility != new_volatility:
            changes.append(("volatility", str(existing.volatility), str(new_volatility)))
            
        new_risk_level = case_data.get("risk_level")
        if existing.risk_level != new_risk_level:
            changes.append(("risk_level", str(existing.risk_level), str(new_risk_level)))
            
        new_max_multiplier = Decimal(str(case_data.get("max_multiplier", 0))) if case_data.get("max_multiplier") else None
        if existing.max_multiplier != new_max_multiplier:
            changes.append(("max_multiplier", str(existing.max_multiplier), str(new_max_multiplier)))
        
        # Check if items changed
        existing_hash = hash_items(existing.items.all())
        new_hash = hash_items_data(case_data.get("items", []))
        items_changed = existing_hash != new_hash
        
        if items_changed:
            changes.append(("items", existing_hash, new_hash))
        
        if changes:
            with transaction.atomic():
                # Update the case
                existing.name = case_data.get("name", "")
                existing.image_url = case_data.get("image", "")
                existing.price_rub = new_price_rub
                existing.price_usd = new_price_usd
                existing.price_eur = new_price_eur
                existing.is_mining_case = case_data.get("is_mining_case", False)
                existing.expected_return = new_expected_return
                existing.volatility = new_volatility
                existing.risk_level = new_risk_level
                existing.max_multiplier = new_max_multiplier
                existing.save()
                
                # Update items if changed
                if items_changed:
                    existing.items.all().delete()
                    for item in case_data.get("items", []):
                        CaseItem.objects.create(
                            case=existing,
                            item_id=item.get("id", ""),
                            name=item.get("name", ""),
                            probability=Decimal(str(item.get("probability", 0))),
                            price_rub=Decimal(str(item.get("price_rub", 0))),
                            price_usd=Decimal(str(item.get("price_usd", 0))) if item.get("price_usd") else None,
                            price_eur=Decimal(str(item.get("price_eur", 0))) if item.get("price_eur") else None,
                        )
                
                # Log history
                for field, old_val, new_val in changes:
                    CaseHistory.objects.create(
                        case=existing,
                        field_changed=field,
                        old_value=old_val,
                        new_value=new_val
                    )
                    
            logger.info(f"Updated case {case_id}: {len(changes)} changes")
            return True
            
        return False
        
    except Case.DoesNotExist:
        # New case - create it
        with transaction.atomic():
            case = Case.objects.create(
                case_id=case_id,
                name=case_data.get("name", ""),
                image_url=case_data.get("image", ""),
                price_rub=Decimal(str(case_data.get("price_rub", 0))),
                price_usd=Decimal(str(case_data.get("price_usd", 0))) if case_data.get("price_usd") else None,
                price_eur=Decimal(str(case_data.get("price_eur", 0))) if case_data.get("price_eur") else None,
                is_mining_case=case_data.get("is_mining_case", False),
                expected_return=Decimal(str(case_data.get("expected_return", 0))) if case_data.get("expected_return") else None,
                volatility=Decimal(str(case_data.get("volatility", 0))) if case_data.get("volatility") else None,
                risk_level=case_data.get("risk_level"),
                max_multiplier=Decimal(str(case_data.get("max_multiplier", 0))) if case_data.get("max_multiplier") else None,
            )
            
            for item in case_data.get("items", []):
                CaseItem.objects.create(
                    case=case,
                    item_id=item.get("id", ""),
                    name=item.get("name", ""),
                    probability=Decimal(str(item.get("probability", 0))),
                    price_rub=Decimal(str(item.get("price_rub", 0))),
                    price_usd=Decimal(str(item.get("price_usd", 0))) if item.get("price_usd") else None,
                    price_eur=Decimal(str(item.get("price_eur", 0))) if item.get("price_eur") else None,
                )
                
        logger.info(f"Created new case {case_id}")
        return True


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_csgonet_cases(self):
    """
    Celery task to refresh CSGO.NET case data.
    Runs every 15 minutes via Celery Beat.
    
    1. Fetches fresh data from CSGO.NET WebSocket
    2. Calculates expected return for each case
    3. Updates Redis cache (always)
    4. Saves to database only if changes detected
    """
    logger.info("Starting CSGO.NET case refresh")
    
    try:
        # 1. Fetch fresh data from WebSocket
        client = CSGONetWebSocketClient(timeout=settings.CSGONET_WEBSOCKET_TIMEOUT)
        cases = client.connect_and_collect()
        
        if not cases:
            logger.warning("No cases received from CSGO.NET")
            raise self.retry(exc=Exception("No cases received"))
        
        logger.info(f"Fetched {len(cases)} cases from CSGO.NET")
        
        # 2. Calculate expected return and volatility for each case
        for case in cases:
            expected_return = calculate_expected_return(case)
            if expected_return is not None:
                case["expected_return"] = expected_return
            
            # Calculate volatility (high risk / high reward metrics)
            volatility_data = calculate_volatility(case)
            if volatility_data is not None:
                case["volatility"] = volatility_data["volatility"]
                case["risk_level"] = volatility_data["risk_level"]
                case["max_multiplier"] = volatility_data["max_multiplier"]
        
        # 3. Prepare cache data
        cache_data = {
            "success": True,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "cases_count": len(cases),
            "cases": cases
        }
        
        # 4. Update Redis cache
        cache.set(
            settings.CSGONET_CACHE_KEY,
            json.dumps(cache_data),
            settings.CSGONET_CACHE_TTL
        )
        logger.info(f"Updated Redis cache with {len(cases)} cases")
        
        # 5. Save to database only if changed
        changes_count = 0
        for case_data in cases:
            if save_case_if_changed(case_data):
                changes_count += 1
                
        logger.info(f"Database updates: {changes_count} cases changed")
        
        return {
            "success": True,
            "cases_fetched": len(cases),
            "changes_saved": changes_count
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh CSGO.NET cases: {e}")
        raise self.retry(exc=e)


@shared_task
def refresh_csgonet_cases_manual():
    """
    Manual trigger for refreshing case data.
    Can be called from Django admin or shell.
    """
    return refresh_csgonet_cases.delay()

