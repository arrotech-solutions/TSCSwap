from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from . import views

app_name = 'users'


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/completion/', views.profile_completion_view, name='profile_completion'),
    path('password/change/', views.password_change_view, name='password_change'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/edit/', views.admin_edit_user_view, name='admin_edit_user'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user_view, name='admin_delete_user'),
    path('admin/unique-subject-combinations/', views.admin_unique_subject_combinations, name='admin_unique_subject_combinations'),
    path('admin/unique-subject-combinations/detail/', views.admin_subject_combination_detail, name='admin_subject_combination_detail'),
    path('admin/unique-locations/', views.admin_unique_locations, name='admin_unique_locations'),
    path('admin/unique-locations/detail/', views.admin_location_detail, name='admin_location_detail'),
    path('admin/unique-fast-swap-combinations/', views.admin_unique_fast_swap_combinations, name='admin_unique_fast_swap_combinations'),
    path('admin/unique-fast-swap-combinations/detail/', views.admin_fast_swap_combination_detail, name='admin_fast_swap_combination_detail'),
    
    # Password reset URLs moved to root urls.py for global access

    # Swap functionality
    path('initiate-swap/<int:user_id>/', views.initiate_swap, name='initiate_swap'),
    path('find-secondary-matches/', views.find_secondary_matches, name='find_secondary_matches'),
    
    # Swap request management
    path('swap-requests/', views.swap_requests, name='swap_requests'),
    path('swap-requests/accept/<int:request_id>/', views.accept_swap_request, name='accept_swap_request'),
    path('swap-requests/reject/<int:request_id>/', views.reject_swap_request, name='reject_swap_request'),
    path('swap-requests/cancel/<int:request_id>/', views.cancel_swap_request, name='cancel_swap_request'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Teaching information
    path('teaching-info/', views.select_teaching_info, name='select_teaching_info'),
    
    # API endpoints
    path('api/levels/<int:level_id>/subjects/', 
         login_required(views.get_subjects_for_level), 
         name='get_subjects_for_level'),
         
    # Teacher management
    path('admin/teachers/<int:user_id>/subjects/', 
         login_required(views.manage_teacher_subjects), 
         name='manage_teacher_subjects'),
    path('admin/primary-matched-swaps/', 
         login_required(views.primary_matched_swaps), 
         name='primary_matched_swaps'),
    path('admin/high-school-matched-swaps/', 
         login_required(views.high_school_matched_swaps), 
         name='high_school_matched_swaps'),
    path('api/levels/<int:level_id>/subjects/', 
         login_required(views.get_subjects_for_level), 
         name='get_subjects_for_level'),
] 