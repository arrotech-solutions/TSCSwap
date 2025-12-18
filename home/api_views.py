from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Constituencies, Wards

class ConstituencyAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
        
    def get(self, request):
        county_id = request.GET.get('county')
        if not county_id:
            return JsonResponse([], safe=False)
            
        try:
            constituencies = Constituencies.objects.filter(county_id=county_id).values('id', 'name').order_by('name')
            return JsonResponse(list(constituencies), safe=False)
        except Exception as e:
            print(f"Error in ConstituencyAPIView: {str(e)}")
            return JsonResponse([], safe=False)

class WardAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
        
    def get(self, request):
        constituency_id = request.GET.get('constituency')
        if not constituency_id:
            return JsonResponse([], safe=False)
            
        try:
            wards = Wards.objects.filter(constituency_id=constituency_id).values('id', 'name').order_by('name')
            return JsonResponse(list(wards), safe=False)
        except Exception as e:
            print(f"Error in WardAPIView: {str(e)}")
            return JsonResponse([], safe=False)
        return JsonResponse(list(wards), safe=False)
