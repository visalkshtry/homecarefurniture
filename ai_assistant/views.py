import time
import json
from django.shortcuts import render

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import AIQueryLog
from .engine import answer as local_answer
from inventory.models import RawMaterial, FinishedGood
from pos.models import Sale
from hr.models import Employee


def _build_context_snapshot():
    from django.utils import timezone
    today = timezone.localdate()
    month_start = today.replace(day=1)

    low_stock = [f"{m.name} ({m.quantity_on_hand} {m.unit})" for m in RawMaterial.objects.all() if m.is_low_stock]
    top_products = list(
        FinishedGood.objects.filter(is_active=True).values('name', 'quantity_on_hand', 'selling_price')[:10]
    )
    monthly_revenue = sum(
        float(s.total_amount) for s in
        Sale.objects.filter(sale_date__date__gte=month_start, status=Sale.STATUS_COMPLETED)
    )
    employee_count = Employee.objects.filter(is_active=True).count()

    return json.dumps({
        'date': str(today),
        'low_stock_materials': low_stock,
        'top_products': top_products,
        'monthly_revenue': monthly_revenue,
        'active_employees': employee_count,
    }, default=str)


SYSTEM_PROMPT = """You are an AI business assistant for Home Care Furniture Udhyog, a furniture manufacturer in Lokanthali, Bhaktapur, Nepal. Prices are in Nepali Rupees (रू).
Use the live business data below to answer accurately. Be concise and actionable.

{context}"""


def _call_claude(api_key, context, query):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(context=context),
        messages=[{"role": "user", "content": query}],
    )
    return message.content[0].text, message.usage.input_tokens, message.usage.output_tokens


def _call_gemini(api_key, context, query):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(f"{SYSTEM_PROMPT.format(context=context)}\n\nUser question: {query}")
    text = response.text
    pt = rt = None
    if hasattr(response, 'usage_metadata'):
        pt = response.usage_metadata.prompt_token_count
        rt = response.usage_metadata.candidates_token_count
    return text, pt, rt


def _get_provider():
    anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '')
    if anthropic_key and anthropic_key not in ('', 'your_anthropic_api_key_here'):
        return 'claude', anthropic_key
    if gemini_key and gemini_key not in ('', 'your_gemini_api_key_here'):
        return 'gemini', gemini_key
    return 'local', None


def ai_dashboard(request):
    recent_queries = AIQueryLog.objects.order_by('-created_at')[:10]
    provider, _ = _get_provider()
    provider_label = {'claude': 'Claude', 'gemini': 'Gemini', 'local': 'Local Engine'}.get(provider, 'Local Engine')
    return render(request, 'ai_assistant/dashboard.html', {
        'recent_queries': recent_queries,
        'ai_provider': provider_label,
        'is_local': provider == 'local',
    })


@require_POST
def ask_ai(request):
    query = request.POST.get('query', '').strip()
    if not query:
        return JsonResponse({'error': 'Empty query'}, status=400)

    provider, api_key = _get_provider()
    start = time.time()
    response_text = ''
    was_successful = True
    error_msg = ''
    prompt_tokens = None
    response_tokens = None

    try:
        if provider == 'claude':
            context = _build_context_snapshot()
            response_text, prompt_tokens, response_tokens = _call_claude(api_key, context, query)
        elif provider == 'gemini':
            context = _build_context_snapshot()
            response_text, prompt_tokens, response_tokens = _call_gemini(api_key, context, query)
        else:
            # Local engine — always works, no API needed
            response_text = local_answer(query)
    except Exception as e:
        was_successful = False
        error_msg = str(e)
        # Fall back to local engine on API failure
        try:
            response_text = local_answer(query)
            response_text += f"\n\n⚠️ (API unavailable, using local engine: {e})"
        except Exception as e2:
            response_text = f'Sorry, I encountered an error: {e2}'

    latency_ms = int((time.time() - start) * 1000)

    AIQueryLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        query=query,
        db_context_snapshot=_build_context_snapshot() if provider == 'local' else '',
        response=response_text,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        latency_ms=latency_ms,
        was_successful=was_successful,
        error_message=error_msg,
    )

    return JsonResponse({'response': response_text, 'latency_ms': latency_ms})
