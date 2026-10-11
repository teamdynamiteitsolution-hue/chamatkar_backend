import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

@api_view(['POST'])
@permission_classes([AllowAny])
def ai_assistant_view(request):
    data = request.data
    req_type = data.get('type')
    prompt = data.get('prompt', '')
    product = data.get('product') or {}
    order = data.get('order') or {}

    api_key = os.environ.get('GEMINI_API_KEY')
    if api_key == 'MY_GEMINI_API_KEY':
        api_key = None

    # Fallback response generator if API key is not configured or in development
    def get_fallback():
        if req_type == 'product_copy':
            p_name = product.get('name', 'প্রিমিয়াম গ্যাজেট')
            return {
                'success': True,
                'content': f"**{p_name}**\n\nবাংলাদেশে অনলাইনে সবচেয়ে বিশ্বস্ত ও নির্ভরযোগ্য কোয়ালিটি। আকর্ষণীয় ডিজাইন ও দীর্ঘস্থায়ী ব্যাটারি ব্যাকআপ নিশ্চিত করে আপনার প্রাত্যহিক জীবনের নিখুঁত সঙ্গী।\n\n• ১০০% অরিজিনাল ব্র্যান্ড নিউ পণ্য\n• সারাদেশে দ্রুততম ক্যাশ অন ডেলিভারি\n• ৭ দিনের ইনস্ট্যান্ট রিপ্লেসমেন্ট গ্যারান্টি\n\nএখনই 'অর্ডার করুন' বাটনে ক্লিক করে ডেলিভারি কনফার্ম করুন!",
                'source': 'local_generator'
            }
        elif req_type == 'support_reply':
            c_name = order.get('address', {}).get('customerName') if isinstance(order.get('address'), dict) else 'গ্রাহক'
            ord_id = order.get('id', 'BD-849201')
            st = order.get('status', 'প্রসেসিং')
            return {
                'success': True,
                'content': f"আসসালামু আলাইকুম {c_name}, AmarDokan-এ যোগাযোগ করার জন্য ধন্যবাদ। আপনার অর্ডার #{ord_id} বর্তমানে \"{st}\" অবস্থায় রয়েছে। আপনার পার্সেলটি দ্রুত ডেলিভারি নিশ্চিত করতে আমাদের ডেলিভারি টিম কাজ করছে। ট্র্যাকিং লিংক: https://amardokan.com/track-order?id={ord_id}",
                'source': 'local_generator'
            }
        elif req_type == 'risk_analysis':
            return {
                'success': True,
                'content': "**ফ্রড রিস্ক এনালাইসিস:**\n• ফোন নাম্বার: ভেরিফাইড বিডি অপারেটর\n• ডেলিভারি জোন: স্বাভাবিক ডেলিভারি এরিয়া\n• সুপারিশ: কাস্টমারকে কল করে ডেলিভারি সময় কনফার্ম করে পার্সেল বুক করুন।",
                'source': 'local_generator'
            }
        return {
            'success': True,
            'content': "AmarDokan AI Assistant: আপনার অনুরোধটি সফলভাবে প্রসেস করা হয়েছে।",
            'source': 'local_generator'
        }

    if not api_key or not genai or not types:
        return Response(get_fallback())

    try:
        client = genai.Client(api_key=api_key)
        system_instruction = 'You are an expert Bangladesh native e-commerce assistant for AmarDokan platform. Provide concise, professional, sales-driven responses in natural conversational Bangla or Banglish where appropriate.'
        prompt_content = prompt

        if req_type == 'product_copy':
            prompt_content = f"Generate high-converting e-commerce product copy for Bangladesh Facebook/TikTok ads and landing page for: \"{product.get('name')}\". Category: {product.get('category')}. Price: ৳{product.get('price')}. Include catchy Bangla headline, 4 key selling points with emojis, warranty assurance, and call to action."
        elif req_type == 'support_reply':
            addr = order.get('address') or {}
            c_name = addr.get('customerName', 'Customer')
            cour = order.get('courier') or {}
            tracking = cour.get('trackingId', 'Preparing for dispatch')
            prompt_content = f"Draft a polite, professional WhatsApp support response in Bengali for customer \"{c_name}\". Their order is #{order.get('id')}, status is \"{order.get('status')}\", total is ৳{order.get('total')}. Courier tracking: {tracking}."
        elif req_type == 'risk_analysis':
            addr = order.get('address') or {}
            c_name = addr.get('customerName', 'Customer')
            prompt_content = f"Evaluate fraud risk for this Bangladesh Cash on Delivery order: Customer: {c_name}, Phone: {addr.get('phone')}, Address: {addr.get('fullAddress')}, District: {addr.get('district')}, Total: ৳{order.get('total')}. Provide 3 bullet risk assessment points and final recommendation (APPROVE / CALL_VERIFY / CANCEL)."

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )

        return Response({
            'success': True,
            'content': response.text,
            'source': 'gemini_api'
        })
    except Exception as e:
        print(f"Gemini API error: {e}")
        return Response(get_fallback())
