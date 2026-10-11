import re

BANGLADESH_DISTRICTS = [
    'Dhaka', 'Gazipur', 'Narayanganj', 'Tangail', 'Narsingdi', 'Manikganj', 'Munshiganj',
    'Faridpur', 'Chittagong', "Cox's Bazar", 'Comilla', 'Feni', 'Noakhali', 'Brahmanbaria',
    'Chandpur', 'Sylhet', 'Moulvibazar', 'Habiganj', 'Sunamganj', 'Rajshahi', 'Bogura',
    'Pabna', 'Sirajganj', 'Naogaon', 'Natore', 'Khulna', 'Jessore', 'Kushtia', 'Satkhira',
    'Bagerhat', 'Barishal', 'Patuakhali', 'Bhola', 'Rangpur', 'Dinajpur', 'Kurigram',
    'Mymensingh', 'Jamalpur', 'Netrokona'
]

DHAKA_SUBURBS = [
    'savar', 'keraniganj', 'dhamrai', 'ashulia', 'tongi', 'gazipur', 'narayanganj'
]

def normalize_bangladesh_phone(phone: str) -> str:
    if not phone:
        return ''
    cleaned = re.sub(r'\D', '', str(phone))
    if cleaned.startswith('880'):
        cleaned = cleaned[2:]
    if cleaned.startswith('80') and len(cleaned) == 12:
        cleaned = cleaned[1:]
    return cleaned

def is_valid_bangladesh_phone(phone: str) -> bool:
    normalized = normalize_bangladesh_phone(phone)
    # Must be 11 digits and start with 013-019
    return bool(re.match(r'^01[3-9]\d{8}$', normalized))

def calculate_delivery_fee(district: str, area: str = '') -> dict:
    norm_district = (district or '').strip().lower()
    norm_area = (area or '').strip().lower()

    if norm_district == 'dhaka':
        is_suburb = any(sub in norm_area for sub in DHAKA_SUBURBS)
        if is_suburb:
            return {'deliveryZone': 'sub_dhaka', 'deliveryFee': 100}
        return {'deliveryZone': 'inside_dhaka', 'deliveryFee': 60}

    if norm_district in ['gazipur', 'narayanganj']:
        return {'deliveryZone': 'sub_dhaka', 'deliveryFee': 100}

    return {'deliveryZone': 'outside_dhaka', 'deliveryFee': 130}

def assess_order_risk(phone: str, address: str, total: float, payment_method: str = 'COD') -> dict:
    score = 10
    factors = []

    normalized = normalize_bangladesh_phone(phone)

    if not is_valid_bangladesh_phone(phone):
        score += 45
        factors.append('Invalid Bangladesh phone number format')

    if normalized.startswith('014') or normalized.startswith('019'):
        score += 5
        factors.append('Banglalink/Teletalk virtual SIM flag')

    if len(str(address or '').strip()) < 15:
        score += 25
        factors.append('Short or ambiguous delivery address')

    if payment_method == 'COD' and total > 5000:
        score += 30
        factors.append('High-value Cash on Delivery order threshold exceeded (>৳5,000)')

    if payment_method in ['BKASH', 'NAGAD', 'SSLCOMMERZ']:
        score = max(5, score - 20)

    score = min(100, max(0, score))
    return {
        'riskScore': score,
        'riskFactors': factors
    }
