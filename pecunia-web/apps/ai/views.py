"""
AI API Views.

API ViewSets and views for AI features.
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum, Count, Avg
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AIRecommendation, AICategorizationLog, AIAnalysisCache
from .serializers import (
    AIRecommendationSerializer,
    AIRecommendationListSerializer,
    AIRecommendationActionSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    CategorizeRequestSerializer,
    CategorizeResponseSerializer,
    BulkCategorizeRequestSerializer,
    InsightsSerializer,
    InsightsResponseSerializer,
)

logger = logging.getLogger(__name__)


class IsPremiumUser(permissions.BasePermission):
    """Permission check for premium users only."""

    message = "This feature requires a premium subscription."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Check if user has premium subscription
        return getattr(request.user, 'is_premium', False) or \
               getattr(request.user, 'subscription_tier', 'free') in ['premium', 'pro', 'enterprise']


class AIRecommendationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI recommendations.

    Provides CRUD operations and custom actions for recommendations.
    """
    serializer_class = AIRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated, IsPremiumUser]

    def get_queryset(self):
        """Filter recommendations for the current user."""
        queryset = AIRecommendation.objects.filter(
            user=self.request.user,
            is_dismissed=False
        )

        # Filter by type
        rec_type = self.request.query_params.get('type')
        if rec_type:
            queryset = queryset.filter(type=rec_type)

        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # Filter expired
        include_expired = self.request.query_params.get('include_expired', 'false')
        if include_expired.lower() != 'true':
            queryset = queryset.filter(
                models.Q(expires_at__isnull=True) |
                models.Q(expires_at__gt=timezone.now())
            )

        return queryset.select_related('related_category', 'related_transaction')

    def get_serializer_class(self):
        """Use lightweight serializer for list views."""
        if self.action == 'list':
            return AIRecommendationListSerializer
        return AIRecommendationSerializer

    def perform_create(self, serializer):
        """Set user on creation."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a recommendation as read."""
        recommendation = self.get_object()
        recommendation.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss a recommendation."""
        recommendation = self.get_object()
        recommendation.dismiss()
        return Response({'status': 'dismissed'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all recommendations as read."""
        count = AIRecommendation.objects.filter(
            user=request.user,
            is_read=False,
            is_dismissed=False
        ).update(is_read=True, updated_at=timezone.now())
        return Response({'status': f'{count} recommendations marked as read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread recommendations."""
        count = AIRecommendation.objects.filter(
            user=request.user,
            is_read=False,
            is_dismissed=False
        ).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def by_priority(self, request):
        """Get recommendations grouped by priority."""
        queryset = self.get_queryset()
        priorities = ['urgent', 'high', 'medium', 'low']
        result = {}
        for priority in priorities:
            items = queryset.filter(priority=priority)[:5]
            result[priority] = AIRecommendationListSerializer(items, many=True).data
        return Response(result)


class CategorizeView(APIView):
    """
    API view for AI-powered transaction categorization.
    """
    permission_classes = [permissions.IsAuthenticated, IsPremiumUser]

    def post(self, request):
        """Categorize a transaction using AI."""
        serializer = CategorizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            # Get transaction details
            if data.get('transaction_id'):
                from apps.transactions.models import Transaction
                transaction = Transaction.objects.get(
                    id=data['transaction_id'],
                    user=request.user
                )
                description = transaction.description
                amount = transaction.amount
                merchant = getattr(transaction, 'merchant', None)
            else:
                description = data.get('description', '')
                amount = data.get('amount')
                merchant = data.get('merchant')

            # Call AI service for categorization
            result = self._categorize_with_ai(
                description=description,
                amount=amount,
                merchant=merchant,
                user=request.user,
                include_confidence=data.get('include_confidence', True),
                include_alternatives=data.get('include_alternatives', False)
            )

            # Log the categorization attempt
            if data.get('transaction_id'):
                AICategorizationLog.objects.create(
                    user=request.user,
                    transaction_id=data['transaction_id'],
                    suggested_category_id=result['category_id'],
                    confidence_score=result.get('confidence_score', 0),
                    reasoning=result.get('reasoning', ''),
                    raw_response=result
                )

            response_serializer = CategorizeResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data)

        except Exception as e:
            logger.exception("Error categorizing transaction")
            return Response(
                {'error': 'An error occurred while categorizing the transaction.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _categorize_with_ai(self, description, amount, merchant, user,
                            include_confidence=True, include_alternatives=False):
        """
        Categorize transaction using AI service.

        This is a placeholder that should be implemented with actual AI integration.
        """
        from apps.transactions.models import TransactionCategory

        # Get user's categories
        categories = TransactionCategory.objects.filter(
            models.Q(user=user) | models.Q(is_default=True)
        ).values('id', 'name', 'icon')

        # Build prompt for AI
        category_list = [f"- {c['name']} (ID: {c['id']})" for c in categories]
        prompt = f"""
        Categorize this transaction:
        Description: {description}
        Amount: {amount}
        Merchant: {merchant or 'Unknown'}

        Available categories:
        {chr(10).join(category_list)}

        Respond with JSON containing:
        - category_id: UUID of the best matching category
        - category_name: Name of the category
        - confidence_score: 0.0 to 1.0
        - reasoning: Brief explanation
        """

        # TODO: Implement actual AI call
        # For now, return a mock response
        default_category = categories.first() if categories else None

        result = {
            'category_id': str(default_category['id']) if default_category else None,
            'category_name': default_category['name'] if default_category else 'Uncategorized',
            'category_icon': default_category.get('icon', 'tag') if default_category else 'tag',
        }

        if include_confidence:
            result['confidence_score'] = 0.85
            result['reasoning'] = 'Categorized based on transaction description analysis.'

        if include_alternatives:
            result['alternatives'] = []

        return result


class BulkCategorizeView(APIView):
    """API view for bulk transaction categorization."""
    permission_classes = [permissions.IsAuthenticated, IsPremiumUser]

    def post(self, request):
        """Categorize multiple transactions."""
        serializer = BulkCategorizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.transactions.models import Transaction

        transactions = Transaction.objects.filter(
            id__in=data['transaction_ids'],
            user=request.user
        )

        results = []
        for transaction in transactions:
            try:
                # Use CategorizeView's logic
                categorize_view = CategorizeView()
                result = categorize_view._categorize_with_ai(
                    description=transaction.description,
                    amount=transaction.amount,
                    merchant=getattr(transaction, 'merchant', None),
                    user=request.user,
                    include_confidence=True,
                    include_alternatives=False
                )

                # Auto-apply if confidence is high enough
                if data.get('auto_apply') and result.get('confidence_score', 0) >= data.get('confidence_threshold', 0.85):
                    transaction.category_id = result['category_id']
                    transaction.save(update_fields=['category_id', 'updated_at'])
                    result['auto_applied'] = True
                else:
                    result['auto_applied'] = False

                result['transaction_id'] = str(transaction.id)
                results.append(result)

            except Exception as e:
                logger.exception(f"Error categorizing transaction {transaction.id}")
                results.append({
                    'transaction_id': str(transaction.id),
                    'error': str(e)
                })

        return Response({
            'results': results,
            'total': len(results),
            'auto_applied': sum(1 for r in results if r.get('auto_applied'))
        })


class ChatView(APIView):
    """
    API view for AI chat with streaming support.
    """
    permission_classes = [permissions.IsAuthenticated, IsPremiumUser]

    def post(self, request):
        """Handle chat message with streaming response."""
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate that messages in history don't contain system role
        messages = request.data.get('messages', [])
        for msg in messages:
            if isinstance(msg, dict) and msg.get('role') == 'system':
                return Response(
                    {'error': 'The system role is not allowed in chat messages.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if streaming is requested
        accept_header = request.headers.get('Accept', '')
        if 'text/event-stream' in accept_header:
            return self._stream_response(request, data)
        else:
            return self._sync_response(request, data)

    def _sync_response(self, request, data):
        """Handle non-streaming chat response."""
        try:
            response_text = self._generate_response(
                message=data['message'],
                context_type=data.get('context_type', 'general'),
                user=request.user,
                session_id=data.get('session_id')
            )

            response_data = {
                'message': response_text,
                'session_id': data.get('session_id') or self._create_session(request.user).id,
                'created_at': timezone.now(),
                'context_type': data.get('context_type', 'general')
            }

            return Response(response_data)

        except Exception as e:
            logger.exception("Error generating chat response")
            return Response(
                {'error': 'An error occurred while generating the response.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _stream_response(self, request, data):
        """Handle streaming chat response using SSE."""

        def event_stream():
            try:
                # Start event
                yield self._format_sse_event('start', {
                    'session_id': str(data.get('session_id') or 'new'),
                    'timestamp': timezone.now().isoformat()
                })

                # Generate response chunks
                for chunk in self._generate_response_stream(
                    message=data['message'],
                    context_type=data.get('context_type', 'general'),
                    user=request.user,
                    session_id=data.get('session_id')
                ):
                    yield self._format_sse_event('chunk', {'content': chunk})

                # End event
                yield self._format_sse_event('end', {
                    'timestamp': timezone.now().isoformat()
                })

            except Exception as e:
                logger.exception("Error in streaming response")
                yield self._format_sse_event('error', {'message': 'An error occurred while streaming the response.'})

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def _format_sse_event(self, event_type, data):
        """Format data as Server-Sent Event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    def _generate_response(self, message, context_type, user, session_id=None):
        """
        Generate AI response (non-streaming).

        This is a placeholder for actual AI integration.
        """
        # Get user context based on context_type
        context = self._build_context(user, context_type)

        # Build system prompt
        system_prompt = self._get_system_prompt(context_type, context)

        # TODO: Implement actual AI call
        # For now, return a mock response
        response = f"I understand you're asking about {context_type}. "
        response += "Based on your financial data, I'd recommend reviewing your recent transactions "
        response += "and comparing them against your budget goals. "
        response += "Would you like me to analyze any specific aspect of your finances?"

        return response

    def _generate_response_stream(self, message, context_type, user, session_id=None):
        """
        Generate AI response with streaming.

        This is a placeholder for actual streaming AI integration.
        """
        import time

        # Get user context
        context = self._build_context(user, context_type)

        # TODO: Implement actual streaming AI call
        # For now, simulate streaming with mock response
        response = f"I understand you're asking about {context_type}. "
        response += "Based on your financial data, I'd recommend reviewing your recent transactions "
        response += "and comparing them against your budget goals. "
        response += "Would you like me to analyze any specific aspect of your finances?"

        # Simulate streaming by yielding words
        words = response.split(' ')
        for i, word in enumerate(words):
            yield word + (' ' if i < len(words) - 1 else '')
            time.sleep(0.05)  # Simulate delay

    def _build_context(self, user, context_type):
        """Build context data for AI based on user and context type."""
        context = {
            'user_name': user.first_name or user.email.split('@')[0],
            'context_type': context_type,
        }

        try:
            # Add relevant financial data based on context
            if context_type in ['transactions', 'general']:
                from apps.transactions.models import Transaction
                recent_count = Transaction.objects.filter(
                    user=user,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).count()
                context['recent_transaction_count'] = recent_count

            if context_type in ['budgets', 'general']:
                # Add budget context if available
                pass

            if context_type in ['savings', 'general']:
                # Add savings context if available
                pass

        except Exception as e:
            logger.warning(f"Could not build full context: {e}")

        return context

    def _get_system_prompt(self, context_type, context):
        """Get system prompt based on context type."""
        base_prompt = """You are a helpful financial assistant for a personal finance app.
        You help users understand their finances, provide advice, and answer questions.
        Be concise, friendly, and always prioritize the user's financial wellbeing.
        """

        context_prompts = {
            'general': "Help with general financial questions and app navigation.",
            'transactions': "Focus on transaction analysis, categorization, and spending patterns.",
            'budgets': "Help with budget creation, tracking, and optimization.",
            'savings': "Provide savings strategies and goal-setting advice.",
            'investments': "Offer general investment guidance (not specific financial advice).",
        }

        return base_prompt + context_prompts.get(context_type, '')

    def _create_session(self, user):
        """Create a new chat session."""
        from .models import ChatSession
        return ChatSession.objects.create(user=user)


class InsightsView(APIView):
    """
    API view for AI-generated financial insights.
    """
    permission_classes = [permissions.IsAuthenticated, IsPremiumUser]

    def get(self, request):
        """Get financial insights for the user."""
        serializer = InsightsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            # Determine date range
            start_date, end_date = self._get_date_range(
                data.get('period', 'month'),
                data.get('start_date'),
                data.get('end_date')
            )

            # Check cache first
            cache_key = f"{start_date}_{end_date}_{','.join(data.get('insight_types', []))}"
            cached = AIAnalysisCache.objects.filter(
                user=request.user,
                analysis_type='insights',
                cache_key=cache_key,
                expires_at__gt=timezone.now()
            ).first()

            if cached:
                return Response(cached.result)

            # Generate insights
            insights = self._generate_insights(
                user=request.user,
                start_date=start_date,
                end_date=end_date,
                insight_types=data.get('insight_types', ['spending_summary', 'category_breakdown', 'trends']),
                include_comparisons=data.get('include_comparisons', True)
            )

            # Cache the result
            AIAnalysisCache.objects.update_or_create(
                user=request.user,
                analysis_type='insights',
                cache_key=cache_key,
                defaults={
                    'result': insights,
                    'expires_at': timezone.now() + timedelta(hours=6)
                }
            )

            return Response(insights)

        except Exception as e:
            logger.exception("Error generating insights")
            return Response(
                {'error': 'An error occurred while generating insights.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_date_range(self, period, start_date=None, end_date=None):
        """Calculate date range based on period."""
        today = timezone.now().date()

        if period == 'custom' and start_date and end_date:
            return start_date, end_date

        if period == 'week':
            start = today - timedelta(days=today.weekday())
            return start, today

        if period == 'month':
            start = today.replace(day=1)
            return start, today

        if period == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start = today.replace(month=quarter_month, day=1)
            return start, today

        if period == 'year':
            start = today.replace(month=1, day=1)
            return start, today

        # Default to month
        return today.replace(day=1), today

    def _generate_insights(self, user, start_date, end_date, insight_types, include_comparisons):
        """Generate financial insights."""
        from apps.transactions.models import Transaction

        # Get transactions for the period
        transactions = Transaction.objects.filter(
            user=user,
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        )

        # Calculate basic metrics
        income = transactions.filter(
            type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        expenses = transactions.filter(
            type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        net_savings = income - expenses
        savings_rate = float(net_savings / income * 100) if income > 0 else 0

        insights = {
            'period_label': f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}",
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_income': float(income),
            'total_expenses': float(expenses),
            'net_savings': float(net_savings),
            'savings_rate': round(savings_rate, 1),
            'generated_at': timezone.now().isoformat(),
        }

        # Add comparisons with previous period
        if include_comparisons:
            period_days = (end_date - start_date).days
            prev_start = start_date - timedelta(days=period_days + 1)
            prev_end = start_date - timedelta(days=1)

            prev_transactions = Transaction.objects.filter(
                user=user,
                transaction_date__gte=prev_start,
                transaction_date__lte=prev_end
            )

            prev_income = prev_transactions.filter(
                type='income'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            prev_expenses = prev_transactions.filter(
                type='expense'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            insights['income_change'] = self._calculate_change(prev_income, income)
            insights['expense_change'] = self._calculate_change(prev_expenses, expenses)
            insights['savings_change'] = self._calculate_change(
                prev_income - prev_expenses, net_savings
            )

        # Category breakdown
        if 'category_breakdown' in insight_types:
            category_data = transactions.filter(
                type='expense'
            ).values(
                'category__name', 'category__icon'
            ).annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')[:10]

            insights['category_breakdown'] = [
                {
                    'category': item['category__name'] or 'Uncategorized',
                    'icon': item['category__icon'] or 'tag',
                    'amount': float(item['total']),
                    'count': item['count'],
                    'percentage': float(item['total'] / expenses * 100) if expenses > 0 else 0
                }
                for item in category_data
            ]

        # Daily spending trend
        if 'trends' in insight_types:
            daily_data = transactions.filter(
                type='expense'
            ).values('transaction_date').annotate(
                total=Sum('amount')
            ).order_by('transaction_date')

            insights['daily_spending'] = [
                {
                    'date': item['transaction_date'].isoformat(),
                    'amount': float(item['total'])
                }
                for item in daily_data
            ]

        # AI summary
        if 'spending_summary' in insight_types:
            insights['ai_summary'] = self._generate_ai_summary(insights)

        # Savings opportunities
        if 'savings_opportunities' in insight_types:
            insights['recommendations'] = self._find_savings_opportunities(
                user, transactions, insights
            )

        return insights

    def _calculate_change(self, previous, current):
        """Calculate percentage change."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return float((current - previous) / previous * 100)

    def _generate_ai_summary(self, insights):
        """Generate AI summary of insights."""
        # TODO: Implement actual AI summary generation
        summary = f"This period, you earned ${insights['total_income']:,.2f} "
        summary += f"and spent ${insights['total_expenses']:,.2f}, "
        summary += f"resulting in net savings of ${insights['net_savings']:,.2f} "
        summary += f"({insights['savings_rate']:.1f}% savings rate). "

        if insights.get('expense_change'):
            if insights['expense_change'] > 0:
                summary += f"Your spending increased by {insights['expense_change']:.1f}% compared to the previous period."
            else:
                summary += f"Great job! Your spending decreased by {abs(insights['expense_change']):.1f}% compared to the previous period."

        return summary

    def _find_savings_opportunities(self, user, transactions, insights):
        """Find potential savings opportunities."""
        # TODO: Implement actual AI-powered savings analysis
        opportunities = []

        # Example: Flag high spending categories
        if insights.get('category_breakdown'):
            for category in insights['category_breakdown'][:3]:
                if category['percentage'] > 30:
                    opportunities.append({
                        'title': f"Review {category['category']} spending",
                        'description': f"Your {category['category']} spending accounts for {category['percentage']:.1f}% of your expenses.",
                        'estimated_savings': category['amount'] * 0.1,
                        'confidence': 0.7,
                        'category': category['category'],
                        'action_type': 'reduce'
                    })

        return opportunities


class ChatHistoryView(APIView):
    """API view for retrieving chat history."""
    permission_classes = [permissions.IsAuthenticated, IsPremiumUser]

    def get(self, request, session_id=None):
        """Get chat history for a session or all sessions."""
        from .models import ChatSession, ChatMessage

        if session_id:
            try:
                session = ChatSession.objects.get(
                    id=session_id,
                    user=request.user
                )
                messages = ChatMessage.objects.filter(session=session)
                return Response({
                    'session_id': str(session.id),
                    'title': session.title,
                    'messages': [
                        {
                            'role': msg.role,
                            'content': msg.content,
                            'created_at': msg.created_at.isoformat()
                        }
                        for msg in messages
                    ]
                })
            except ChatSession.DoesNotExist:
                return Response(
                    {'error': 'Session not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            sessions = ChatSession.objects.filter(
                user=request.user
            ).order_by('-updated_at')[:20]

            return Response({
                'sessions': [
                    {
                        'id': str(s.id),
                        'title': s.title,
                        'created_at': s.created_at.isoformat(),
                        'updated_at': s.updated_at.isoformat()
                    }
                    for s in sessions
                ]
            })

    def delete(self, request, session_id):
        """Delete a chat session."""
        from .models import ChatSession

        try:
            session = ChatSession.objects.get(
                id=session_id,
                user=request.user
            )
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
