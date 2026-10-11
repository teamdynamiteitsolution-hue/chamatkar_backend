import os
import urllib.parse
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from .models import TranslationCache

logger = logging.getLogger(__name__)

# Fallback Gemini setup if available
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

GOOGLE_TRANSLATE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': '*/*',
}

def _fetch_google_translate(text: str, source_lang: str = 'auto', target_lang: str = 'bn') -> str:
    """
    Calls Google Translate API via dict-chrome-ex client.
    Handles segment joining for multi-line and compound sentences.
    """
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=dict-chrome-ex&sl={source_lang}&tl={target_lang}&dt=t&q={encoded_text}"
    
    response = requests.get(url, headers=GOOGLE_TRANSLATE_HEADERS, timeout=6)
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            segments = [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
            translated = "".join(segments).strip()
            if translated:
                return translated
    raise Exception(f"Google Translate returned status {response.status_code}")

def _fetch_gemini_translate(text: str, source_lang: str = 'auto', target_lang: str = 'bn') -> str:
    """
    Optional Gemini AI translation fallback for highly contextual e-commerce terms.
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key or api_key == 'MY_GEMINI_API_KEY' or not genai:
        raise Exception("Gemini API key not configured")

    client = genai.Client(api_key=api_key)
    prompt = (
        f"You are a professional Bangladeshi e-commerce translator. "
        f"Translate the following text accurately between English and Bengali.\n"
        f"Source language: {source_lang}\n"
        f"Target language: {target_lang} ({'Bengali / বাংলা' if target_lang == 'bn' else 'English'})\n"
        f"Output ONLY the translated text without explanations or quotation marks.\n\n"
        f"Text to translate:\n{text}"
    )
    res = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    if res and res.text:
        return res.text.strip()
    raise Exception("Empty Gemini response")

def translate_text(text: str, source_lang: str = 'auto', target_lang: str = 'bn', use_cache: bool = True) -> str:
    """
    Translates a single string between languages.
    Checks DB cache first, calls external engine if not found, and saves result.
    """
    clean_text = (text or '').strip()
    if not clean_text:
        return ''

    # If source and target are the same, return as is
    if source_lang == target_lang and source_lang != 'auto':
        return clean_text

    # 1. Check DB Cache
    cache_key = TranslationCache.generate_cache_key(clean_text, source_lang, target_lang)
    if use_cache:
        try:
            cached_entry = TranslationCache.objects.filter(cache_key=cache_key).first()
            if cached_entry:
                # Increment hit count asynchronously or softly
                TranslationCache.objects.filter(cache_key=cache_key).update(hit_count=cached_entry.hit_count + 1)
                return cached_entry.translated_text
        except Exception as e:
            logger.warning(f"TranslationCache read error: {e}")

    # 2. Call Translation Engine
    translated = None
    try:
        translated = _fetch_google_translate(clean_text, source_lang, target_lang)
    except Exception as e:
        logger.warning(f"Google translate primary failed: {e}. Trying Gemini or fallback...")
        try:
            translated = _fetch_gemini_translate(clean_text, source_lang, target_lang)
        except Exception as g_err:
            logger.error(f"Gemini fallback also failed: {g_err}")

    # If all dynamic engines fail, return original text safely
    if not translated:
        return clean_text

    # 3. Store in DB Cache for future instant hits
    if use_cache:
        try:
            TranslationCache.objects.update_or_create(
                cache_key=cache_key,
                defaults={
                    'source_text': clean_text,
                    'translated_text': translated,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to write to TranslationCache: {e}")

    return translated

def batch_translate(texts: list, source_lang: str = 'auto', target_lang: str = 'bn') -> list:
    """
    Translates a list of strings in parallel, using bulk cache lookups for speed.
    """
    if not texts:
        return []

    results = [None] * len(texts)
    uncached_indices = []

    # 1. Bulk check DB cache
    keys = [TranslationCache.generate_cache_key((t or '').strip(), source_lang, target_lang) for t in texts]
    try:
        cached_rows = {row.cache_key: row.translated_text for row in TranslationCache.objects.filter(cache_key__in=keys)}
    except Exception:
        cached_rows = {}

    for idx, (t, k) in enumerate(zip(texts, keys)):
        cleaned = (t or '').strip()
        if not cleaned:
            results[idx] = ''
        elif k in cached_rows:
            results[idx] = cached_rows[k]
        else:
            uncached_indices.append(idx)

    # 2. For any uncached items, fetch concurrently (max 5 workers to avoid rate limits)
    if uncached_indices:
        def _fetch_item(i):
            text_to_translate = texts[i]
            translated_result = translate_text(text_to_translate, source_lang, target_lang, use_cache=True)
            return (i, translated_result)

        with ThreadPoolExecutor(max_workers=10) as executor:
            for i, trans in executor.map(_fetch_item, uncached_indices):
                results[i] = trans

    return results
