from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.http import JsonResponse
from .models import Branch
import uuid

class BranchMiddleware(MiddlewareMixin):
    
    def process_request(self, request):
        # Reset branch context
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_branch_id = ''")
        
        # Get branch ID from request
        branch_id = self._get_branch_id(request)
        
        if branch_id:
            try:
                # Validate UUID format first
                uuid.UUID(branch_id)
                
                # Set branch context FIRST (before querying)
                with connection.cursor() as cursor:
                    cursor.execute("SET app.current_branch_id = %s", [str(branch_id)])
                
                # Now validate branch exists (with RLS context applied)
                branch = Branch.objects.filter(id=branch_id, is_active=True).first()
                if not branch:
                    # Reset context if invalid
                    with connection.cursor() as cursor:
                        cursor.execute("SET app.current_branch_id = ''")
                    return JsonResponse({'error': 'Invalid branch'}, status=403)
                
                # Add to request object
                request.branch_id = branch_id
                request.branch = branch
                
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid branch ID format'}, status=400)
            except Exception as e:
                # Reset context on any error
                with connection.cursor() as cursor:
                    cursor.execute("SET app.current_branch_id = ''")
                return JsonResponse({'error': 'Branch validation failed'}, status=400)
        else:
            request.branch_id = None
            request.branch = None
            
            # Require branch for API endpoints
            if request.path.startswith('/api/') and request.path != '/api/context-status/':
                return JsonResponse({'error': 'Branch ID required'}, status=400)
    
    def _get_branch_id(self, request):
        # From header (primary method)
        branch_id = request.META.get('HTTP_X_BRANCH_ID')
        if branch_id:
            return branch_id
        
        # From URL params
        branch_id = request.GET.get('branch_id')
        if branch_id:
            return branch_id
        
        # From POST data
        if request.method == 'POST':
            try:
                import json
                data = json.loads(request.body)
                return data.get('branch_id')
            except:
                pass
        
        return None

    def process_response(self, request, response):
        # Clean up branch context
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_branch_id = ''")
        return response