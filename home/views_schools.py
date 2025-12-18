import logging
from django.http import JsonResponse
from django.db.models import Q
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Schools

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class SchoolSearchView(View):
    def get(self, request):
        try:
            query = request.GET.get('q', '').strip()
            logger.info(f"School search query: {query}")
            
            if not query or len(query) < 2:
                return JsonResponse({'schools': [], 'status': 'success'})
                
            # Search by school name only
            schools = Schools.objects.select_related('ward__constituency__county').filter(name__icontains=query).order_by('name')[:10] 
                                 
                                  # Limit to 10 results, ordered by name
            
            # Debug: Log the raw query and results
            logger.info(f"Raw SQL: {str(schools.query)}")
            logger.info(f"Found {schools.count()} schools matching: {query}")
            
            results = []
            for school in schools:
                try:
                    results.append({
                        'id': school.id,
                        'name': school.name,
                        'type': school.get_level_display() if hasattr(school, 'get_level_display') else 'N/A',
                        'gender': school.get_gender_display(),
                        'boarding': school.get_boarding_display(),
                        'location': f"{school.ward}, {school.ward.constituency}, {school.ward.constituency.county}",
                    })
                except Exception as e:
                    logger.error(f"Error processing school {school.id}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(results)} schools for query: {query}")
            return JsonResponse({
                'schools': results,
                'status': 'success',
                'query': query
            })
            
        except Exception as e:
            logger.error(f"Error in SchoolSearchView: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'An error occurred while searching for schools',
                'status': 'error'
            }, status=500)

class AttachSchoolView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
            
        school_id = request.POST.get('school_id')
        try:
            school = Schools.objects.get(id=school_id)
            profile = request.user.profile
            profile.school = school
            profile.save()
            return JsonResponse({
                'success': True,
                'school': {
                    'id': school.id,
                    'name': school.name,
                    'location': f"{school.ward}, {school.ward.constituency}"
                }
            })
        except Schools.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'School not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
