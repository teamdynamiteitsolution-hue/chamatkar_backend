from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .services import translate_text, batch_translate
from .models import TranslationCache

@api_view(['POST'])
@permission_classes([AllowAny])
def translate_single(request):
    """
    Translates a single text string (used by Admin Inventory field auto-convert).
    """
    data = request.data or {}
    text = data.get('text', '')
    source_lang = data.get('source', 'auto')
    target_lang = data.get('target', 'bn')

    if not text or not str(text).strip():
        return Response({
            'success': True,
            'translated': '',
            'original': '',
            'source': source_lang,
            'target': target_lang,
        })

    try:
        translated = translate_text(text=str(text), source_lang=source_lang, target_lang=target_lang)
        return Response({
            'success': True,
            'translated': translated,
            'original': text,
            'source': source_lang,
            'target': target_lang,
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'translated': text,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def translate_batch(request):
    """
    Translates multiple strings in bulk (used by Storefront / Landing page dynamic elements).
    """
    data = request.data or {}
    texts = data.get('texts', [])
    source_lang = data.get('source', 'auto')
    target_lang = data.get('target', 'bn')

    if not isinstance(texts, list):
        return Response({'success': False, 'error': "'texts' must be an array of strings"}, status=status.HTTP_400_BAD_REQUEST)

    if not texts:
        return Response({'success': True, 'translations': []})

    # Limit max batch size per request to 100 items for safety
    bounded_texts = texts[:100]

    try:
        results = batch_translate(bounded_texts, source_lang=source_lang, target_lang=target_lang)
        return Response({
            'success': True,
            'translations': results,
            'count': len(results),
            'source': source_lang,
            'target': target_lang,
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'translations': texts,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def translator_status(request):
    """
    Returns current health status and cache statistics of the Translator engine.
    """
    total_cached = TranslationCache.objects.count()
    return Response({
        'status': 'online',
        'engine': 'realtime_neural_gtx',
        'cache_entries': total_cached,
        'supported_pairs': ['en->bn', 'bn->en', 'auto->bn', 'auto->en'],
    })
