"""
AI Template Views.

Django views for rendering AI feature templates.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from .models import AIRecommendation, AIAnalysisCache


def premium_required(view_func):
    """Decorator to check for premium subscription."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('accounts:login')

        is_premium = getattr(request.user, 'is_premium', False) or \
                     getattr(request.user, 'subscription_tier', 'free') in ['premium', 'pro', 'enterprise']

        if not is_premium:
            return render(request, 'ai/premium_required.html', {
                'feature': 'AI Features',
                'description': 'Unlock AI-powered insights, recommendations, and chat assistance.',
            })

        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@premium_required
def recommendations_list(request):
    """
    Display list of AI recommendations.

    Supports filtering, pagination, and HTMX partial updates.
    """
    # Get filter parameters
    priority = request.GET.get('priority')
    rec_type = request.GET.get('type')
    status_filter = request.GET.get('status', 'active')
    page = request.GET.get('page', 1)

    # Build queryset
    queryset = AIRecommendation.objects.filter(user=request.user)

    # Apply filters
    if status_filter == 'active':
        queryset = queryset.filter(is_dismissed=False)
    elif status_filter == 'read':
        queryset = queryset.filter(is_read=True, is_dismissed=False)
    elif status_filter == 'unread':
        queryset = queryset.filter(is_read=False, is_dismissed=False)
    elif status_filter == 'dismissed':
        queryset = queryset.filter(is_dismissed=True)

    if priority:
        queryset = queryset.filter(priority=priority)

    if rec_type:
        queryset = queryset.filter(type=rec_type)

    # Exclude expired recommendations by default
    queryset = queryset.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )

    # Order by priority and date
    priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
    queryset = queryset.extra(
        select={'priority_order': "CASE WHEN priority='urgent' THEN 0 WHEN priority='high' THEN 1 WHEN priority='medium' THEN 2 ELSE 3 END"}
    ).order_by('priority_order', '-created_at')

    # Get counts for badges
    counts = {
        'total': AIRecommendation.objects.filter(user=request.user, is_dismissed=False).count(),
        'unread': AIRecommendation.objects.filter(user=request.user, is_read=False, is_dismissed=False).count(),
        'urgent': AIRecommendation.objects.filter(user=request.user, priority='urgent', is_dismissed=False).count(),
    }

    # Paginate
    paginator = Paginator(queryset, 10)
    recommendations = paginator.get_page(page)

    # Get recommendation types for filter
    types = AIRecommendation.TYPE_CHOICES
    priorities = AIRecommendation.PRIORITY_CHOICES

    context = {
        'recommendations': recommendations,
        'counts': counts,
        'types': types,
        'priorities': priorities,
        'current_filters': {
            'priority': priority,
            'type': rec_type,
            'status': status_filter,
        },
    }

    # Return partial for HTMX requests
    if request.headers.get('HX-Request'):
        return render(request, 'ai/partials/recommendations_list.html', context)

    return render(request, 'ai/recommendations.html', context)


@login_required
@premium_required
@require_POST
def recommendation_action(request, pk):
    """Handle recommendation actions (mark read, dismiss)."""
    recommendation = get_object_or_404(
        AIRecommendation,
        pk=pk,
        user=request.user
    )

    action = request.POST.get('action')

    if action == 'mark_read':
        recommendation.mark_as_read()
    elif action == 'dismiss':
        recommendation.dismiss()
    elif action == 'restore':
        recommendation.is_dismissed = False
        recommendation.save(update_fields=['is_dismissed', 'updated_at'])

    # For HTMX requests, return updated card or empty response
    if request.headers.get('HX-Request'):
        if action == 'dismiss':
            return HttpResponse('')  # Remove from list
        return render(request, 'ai/partials/recommendation_card.html', {
            'recommendation': recommendation
        })

    return JsonResponse({'status': 'success'})


@login_required
@premium_required
@require_POST
def mark_all_read(request):
    """Mark all recommendations as read."""
    count = AIRecommendation.objects.filter(
        user=request.user,
        is_read=False,
        is_dismissed=False
    ).update(is_read=True, updated_at=timezone.now())

    if request.headers.get('HX-Request'):
        return HttpResponse(
            f'<span class="text-success">{count} marked as read</span>',
            headers={'HX-Trigger': 'recommendationsUpdated'}
        )

    return JsonResponse({'status': 'success', 'count': count})


@login_required
@premium_required
def chat_interface(request):
    """
    Display AI chat interface.

    Supports real-time streaming responses.
    """
    from .models import ChatSession, ChatMessage

    # Get or create active session
    session_id = request.GET.get('session')
    session = None
    messages = []

    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            messages = list(ChatMessage.objects.filter(session=session).values(
                'role', 'content', 'created_at'
            ))
        except ChatSession.DoesNotExist:
            pass

    # Get recent sessions for sidebar
    recent_sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by('-updated_at')[:10]

    # Context suggestions based on user's data
    context_suggestions = _get_context_suggestions(request.user)

    context = {
        'session': session,
        'messages': messages,
        'recent_sessions': recent_sessions,
        'context_suggestions': context_suggestions,
        'context_types': [
            {'value': 'general', 'label': 'General Finance', 'icon': 'chat-dots'},
            {'value': 'transactions', 'label': 'Transactions', 'icon': 'receipt'},
            {'value': 'budgets', 'label': 'Budgets', 'icon': 'piggy-bank'},
            {'value': 'savings', 'label': 'Savings', 'icon': 'coin'},
            {'value': 'investments', 'label': 'Investments', 'icon': 'graph-up'},
        ],
    }

    return render(request, 'ai/chat.html', context)


@login_required
@premium_required
@require_POST
def chat_send(request):
    """
    Handle chat message submission via HTMX.

    Returns the user message immediately and triggers streaming response.
    """
    from .models import ChatSession, ChatMessage

    message = request.POST.get('message', '').strip()
    session_id = request.POST.get('session_id')
    context_type = request.POST.get('context_type', 'general')

    if not message:
        return HttpResponse('', status=400)

    # Get or create session
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            session = ChatSession.objects.create(user=request.user)
    else:
        session = ChatSession.objects.create(
            user=request.user,
            title=message[:50] + '...' if len(message) > 50 else message
        )

    # Save user message
    ChatMessage.objects.create(
        session=session,
        role='user',
        content=message
    )

    # Update session
    session.context = {'type': context_type}
    session.save(update_fields=['context', 'updated_at'])

    # Return user message HTML with trigger for AI response
    return render(request, 'ai/partials/chat_message.html', {
        'message': {
            'role': 'user',
            'content': message,
            'created_at': timezone.now()
        },
        'session_id': str(session.id),
        'trigger_response': True
    })


@login_required
@premium_required
def chat_stream(request, session_id):
    """
    Stream AI response via Server-Sent Events.
    """
    from django.http import StreamingHttpResponse
    from .models import ChatSession, ChatMessage

    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return HttpResponse('Session not found', status=404)

    # Get recent messages for context
    recent_messages = ChatMessage.objects.filter(session=session).order_by('-created_at')[:10]
    messages = list(reversed(recent_messages.values('role', 'content')))

    def event_stream():
        import time

        # Get the last user message
        user_message = messages[-1]['content'] if messages else ''
        context_type = session.context.get('type', 'general')

        # Build context
        context = _build_chat_context(request.user, context_type)

        # Generate response (placeholder - replace with actual AI call)
        response_text = _generate_ai_response(user_message, context_type, context, messages)

        # Start event
        yield f"event: start\ndata: {json.dumps({'session_id': str(session.id)})}\n\n"

        # Stream response word by word
        words = response_text.split(' ')
        full_response = []

        for i, word in enumerate(words):
            chunk = word + (' ' if i < len(words) - 1 else '')
            full_response.append(chunk)
            yield f"event: chunk\ndata: {json.dumps({'content': chunk})}\n\n"
            time.sleep(0.03)

        # Save assistant message
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=''.join(full_response)
        )

        # End event
        yield f"event: end\ndata: {json.dumps({'complete': True})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@premium_required
@require_POST
def chat_new_session(request):
    """Create a new chat session."""
    from .models import ChatSession

    session = ChatSession.objects.create(user=request.user)

    if request.headers.get('HX-Request'):
        return render(request, 'ai/partials/chat_session_item.html', {
            'session': session,
            'is_active': True
        })

    return JsonResponse({
        'session_id': str(session.id),
        'title': session.title
    })


@login_required
@premium_required
@require_http_methods(['DELETE'])
def chat_delete_session(request, session_id):
    """Delete a chat session."""
    from .models import ChatSession

    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
    except ChatSession.DoesNotExist:
        pass

    if request.headers.get('HX-Request'):
        return HttpResponse('')

    return JsonResponse({'status': 'deleted'})


@login_required
@premium_required
def insights_dashboard(request):
    """
    Display AI insights dashboard.

    Shows monthly insights, charts, and AI suggestions.
    """
    # Get period from request
    period = request.GET.get('period', 'month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Calculate date range
    today = timezone.now().date()

    if period == 'week':
        start = today - timedelta(days=today.weekday())
        end = today
        period_label = 'This Week'
    elif period == 'month':
        start = today.replace(day=1)
        end = today
        period_label = 'This Month'
    elif period == 'quarter':
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        end = today
        period_label = 'This Quarter'
    elif period == 'year':
        start = today.replace(month=1, day=1)
        end = today
        period_label = 'This Year'
    elif period == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        period_label = f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    else:
        start = today.replace(day=1)
        end = today
        period_label = 'This Month'

    # Get insights data
    insights = _generate_insights_data(request.user, start, end)

    # Get AI recommendations related to insights
    recommendations = AIRecommendation.objects.filter(
        user=request.user,
        is_dismissed=False,
        type__in=['spending', 'saving', 'budget', 'trend']
    ).order_by('-created_at')[:5]

    context = {
        'insights': insights,
        'recommendations': recommendations,
        'period': period,
        'period_label': period_label,
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'periods': [
            {'value': 'week', 'label': 'This Week'},
            {'value': 'month', 'label': 'This Month'},
            {'value': 'quarter', 'label': 'This Quarter'},
            {'value': 'year', 'label': 'This Year'},
            {'value': 'custom', 'label': 'Custom Range'},
        ],
    }

    # Return partial for HTMX requests
    if request.headers.get('HX-Request'):
        return render(request, 'ai/partials/insights_content.html', context)

    return render(request, 'ai/insights.html', context)


def _get_context_suggestions(user):
    """Get context-aware suggestions for chat."""
    suggestions = [
        "How's my spending this month?",
        "What are my top expense categories?",
        "Can you help me create a budget?",
        "Where can I save more money?",
    ]

    # Add personalized suggestions based on user data
    try:
        unread_count = AIRecommendation.objects.filter(
            user=user, is_read=False, is_dismissed=False
        ).count()
        if unread_count > 0:
            suggestions.insert(0, f"Tell me about my {unread_count} new recommendations")
    except Exception:
        pass

    return suggestions[:5]


def _build_chat_context(user, context_type):
    """Build context data for AI chat."""
    context = {
        'user_name': user.first_name or user.email.split('@')[0],
        'context_type': context_type,
    }

    try:
        from apps.transactions.models import Transaction

        # Add basic financial context
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_transactions = Transaction.objects.filter(
            user=user,
            date__gte=thirty_days_ago
        )

        context['transaction_count'] = recent_transactions.count()
        context['total_spent'] = float(
            recent_transactions.filter(transaction_type='expense').aggregate(
                total=Sum('amount')
            )['total'] or 0
        )
    except Exception:
        pass

    return context


def _generate_ai_response(message, context_type, context, history):
    """
    Generate AI response.

    Placeholder for actual AI integration.
    """
    message_lower = message.lower()

    # Simple keyword-based responses (replace with actual AI)
    if 'spending' in message_lower or 'spent' in message_lower:
        total = context.get('total_spent', 0)
        return f"Based on your recent transactions, you've spent ${total:,.2f} in the last 30 days. Would you like me to break this down by category or analyze any specific spending patterns?"

    if 'budget' in message_lower:
        return "I can help you create or review your budget. To get started, I'll need to analyze your income and typical expenses. Would you like me to suggest budget categories based on your transaction history?"

    if 'save' in message_lower or 'saving' in message_lower:
        return "Great question about savings! Based on your financial patterns, here are a few strategies that might work for you: 1) Set up automatic transfers to a savings account, 2) Use the 50/30/20 rule for budgeting, 3) Track and reduce recurring subscriptions. Would you like me to elaborate on any of these?"

    if 'recommend' in message_lower:
        return "I have several personalized recommendations for you based on your spending patterns. You can view them in the Recommendations tab, or I can summarize the most important ones here. What would you prefer?"

    # Default response
    return f"I understand you're asking about {context_type}. Based on your recent activity ({context.get('transaction_count', 0)} transactions), I can help you analyze your finances, create budgets, or find savings opportunities. What specific aspect would you like to explore?"


def _generate_insights_data(user, start_date, end_date):
    """Generate insights data for dashboard."""
    try:
        from apps.transactions.models import Transaction

        transactions = Transaction.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        )

        # Calculate totals
        income = transactions.filter(
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        expenses = transactions.filter(
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        net_savings = income - expenses
        savings_rate = float(net_savings / income * 100) if income > 0 else 0

        # Category breakdown
        category_data = transactions.filter(
            transaction_type='expense'
        ).values(
            'category__name', 'category__icon', 'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:8]

        categories = [
            {
                'name': item['category__name'] or 'Uncategorized',
                'icon': item['category__icon'] or 'tag',
                'color': item['category__color'] or '#6c757d',
                'amount': float(item['total']),
                'count': item['count'],
                'percentage': float(item['total'] / expenses * 100) if expenses > 0 else 0
            }
            for item in category_data
        ]

        # Daily spending for chart
        daily_data = transactions.filter(
            transaction_type='expense'
        ).values('date').annotate(
            total=Sum('amount')
        ).order_by('date')

        daily_spending = [
            {
                'date': item['date'].isoformat(),
                'label': item['date'].strftime('%b %d'),
                'amount': float(item['total'])
            }
            for item in daily_data
        ]

        # Previous period comparison
        period_days = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_days + 1)
        prev_end = start_date - timedelta(days=1)

        prev_transactions = Transaction.objects.filter(
            user=user,
            date__gte=prev_start,
            date__lte=prev_end
        )

        prev_income = prev_transactions.filter(
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        prev_expenses = prev_transactions.filter(
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        def calc_change(prev, curr):
            if prev == 0:
                return 100.0 if curr > 0 else 0.0
            return float((curr - prev) / prev * 100)

        return {
            'total_income': float(income),
            'total_expenses': float(expenses),
            'net_savings': float(net_savings),
            'savings_rate': round(savings_rate, 1),
            'transaction_count': transactions.count(),
            'categories': categories,
            'daily_spending': daily_spending,
            'income_change': round(calc_change(prev_income, income), 1),
            'expense_change': round(calc_change(prev_expenses, expenses), 1),
            'savings_change': round(calc_change(prev_income - prev_expenses, net_savings), 1),
            'ai_summary': _generate_insight_summary(
                float(income), float(expenses), float(net_savings), savings_rate, categories
            ),
        }

    except Exception as e:
        # Return default data if transactions app not available
        return {
            'total_income': 0,
            'total_expenses': 0,
            'net_savings': 0,
            'savings_rate': 0,
            'transaction_count': 0,
            'categories': [],
            'daily_spending': [],
            'income_change': 0,
            'expense_change': 0,
            'savings_change': 0,
            'ai_summary': 'Unable to generate insights. Please add some transactions first.',
        }


def _generate_insight_summary(income, expenses, savings, rate, categories):
    """Generate AI summary for insights."""
    summary_parts = []

    if income > 0:
        summary_parts.append(f"You earned ${income:,.2f} this period")

    if expenses > 0:
        summary_parts.append(f"and spent ${expenses:,.2f}")

    if savings > 0:
        summary_parts.append(f"You saved ${savings:,.2f} ({rate:.1f}% savings rate).")
    elif savings < 0:
        summary_parts.append(f"You overspent by ${abs(savings):,.2f}.")
    else:
        summary_parts.append("You broke even.")

    if categories:
        top_category = categories[0]
        summary_parts.append(
            f"Your biggest expense category was {top_category['name']} "
            f"at ${top_category['amount']:,.2f} ({top_category['percentage']:.1f}% of spending)."
        )

    return ' '.join(summary_parts)
