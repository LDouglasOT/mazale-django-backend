
import numpy as np
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from collections import defaultdict
import math

class DatingRecommendationEngine:
    """Advanced ML-based recommendation engine for dating app"""
    
    def __init__(self, user):
        self.user = user
        self.preference_profile = self._get_or_create_preference_profile()
    
    def _get_or_create_preference_profile(self):
        from .models import UserPreferenceProfile
        profile, created = UserPreferenceProfile.objects.get_or_create(user=self.user)
        return profile
    
    def calculate_compatibility_score(self, candidate_user):
        """
        Calculate comprehensive compatibility score between users
        Returns score between 0-100
        """
        scores = {
            'demographic': self._demographic_compatibility(candidate_user),
            'behavioral': self._behavioral_compatibility(candidate_user),
            'interest': self._interest_compatibility(candidate_user),
            'engagement': self._engagement_potential(candidate_user),
            'reciprocity': self._reciprocity_score(candidate_user),
            'freshness': self._freshness_score(candidate_user),
            'activity_match': self._activity_level_match(candidate_user)
        }
        
        weights = {
            'demographic': 0.15,
            'behavioral': 0.20,
            'interest': 0.20,
            'engagement': 0.15,
            'reciprocity': 0.15,
            'freshness': 0.10,
            'activity_match': 0.05
        }
        
        final_score = sum(scores[key] * weights[key] for key in scores)
        
        final_score *= candidate_user.recommendation_boost
        
        return min(final_score, 100)
    
    def _demographic_compatibility(self, candidate):
        """Calculate demographic compatibility (age, location, gender preference)"""
        score = 100
        
        if self.user.year and candidate.year:
            user_age = timezone.now().year - int(self.user.year)
            candidate_age = timezone.now().year - int(candidate.year)
            
            age_diff = abs(user_age - candidate_age)
            min_pref = self.preference_profile.age_preference_min
            max_pref = self.preference_profile.age_preference_max
            
            if candidate_age < min_pref or candidate_age > max_pref:
                score *= 0.5
            elif age_diff <= 3:
                score *= 1.0
            elif age_diff <= 7:
                score *= 0.9
            else:
                score *= 0.7
        
        if self.user.latitude and self.user.longitude and candidate.latitude and candidate.longitude:
            distance = self._calculate_distance(
                float(self.user.latitude), float(self.user.longitude),
                float(candidate.latitude), float(candidate.longitude)
            )
            
            distance_importance = self.preference_profile.distance_importance
            if distance <= 10:
                score *= 1.0
            elif distance <= 50:
                score *= (1 - (distance_importance * 0.2))
            elif distance <= 100:
                score *= (1 - (distance_importance * 0.4))
            else:
                score *= (1 - (distance_importance * 0.6))
        
        return score
    
    def _behavioral_compatibility(self, candidate):
        """Analyze behavioral patterns for compatibility"""
        from .models import UserInteraction, ProfileView
        
        score = 100
        
        similar_interactions = UserInteraction.objects.filter(
            user=self.user,
            interaction_type__in=['like', 'superlike', 'message_sent']
        ).select_related('target_user')
        
        if similar_interactions.exists():
            liked_profiles = [i.target_user for i in similar_interactions if i.target_user]
            
            similarity_scores = []
            for liked_user in liked_profiles[:20]:
                similarity = self._calculate_profile_similarity(candidate, liked_user)
                similarity_scores.append(similarity)
            
            if similarity_scores:
                avg_similarity = np.mean(similarity_scores)
                score *= (0.5 + avg_similarity * 0.5)
        
        profile_views = ProfileView.objects.filter(
            viewer=self.user,
            view_duration__gte=10
        ).select_related('viewed_user')
        
        if profile_views.exists():
            engaged_views = profile_views.filter(
                Q(scrolled_to_bottom=True) | Q(viewed_images_count__gte=3)
            )
            engagement_rate = engaged_views.count() / profile_views.count()
            
            engaged_profiles = [pv.viewed_user for pv in engaged_views]
            if engaged_profiles:
                candidate_similarity = np.mean([
                    self._calculate_profile_similarity(candidate, ep)
                    for ep in engaged_profiles[:10]
                ])
                score *= (0.8 + candidate_similarity * 0.4)
        
        return score
    
    def _interest_compatibility(self, candidate):
        """Calculate interest overlap and compatibility"""
        score = 50
        
        user_interests = set(self.user.user_interests or [])
        candidate_interests = set(candidate.user_interests or [])
        
        if user_interests and candidate_interests:
            intersection = len(user_interests & candidate_interests)
            union = len(user_interests | candidate_interests)
            jaccard = intersection / union if union > 0 else 0
            
            score = 50 + (jaccard * 50)
            
            if intersection > 0:
                score *= 1.1
        
        return min(score, 100)
    
    def _engagement_potential(self, candidate):
        """Predict likelihood of mutual engagement"""
        from .models import UserInteraction
        
        score = 70
        
        candidate_messages = UserInteraction.objects.filter(
            target_user=candidate,
            interaction_type='message_sent'
        ).count()
        
        if candidate.online:
            score *= 1.2
        elif candidate.last_login:
            hours_since_login = (timezone.now() - candidate.last_login).total_seconds() / 3600
            if hours_since_login < 24:
                score *= 1.1
            elif hours_since_login < 72:
                score *= 1.0
            else:
                score *= 0.8
        
        if candidate.activity_level in ['high', 'very_high']:
            score *= 1.15
        
        completeness = self._calculate_profile_completeness(candidate)
        score *= (0.7 + completeness * 0.3)
        
        return min(score, 100)
    
    def _reciprocity_score(self, candidate):
        """Calculate likelihood of reciprocal interest"""
        from .models import ProfileView, ProfileLike
        
        score = 50
        
        candidate_viewed_us = ProfileView.objects.filter(
            viewer=candidate,
            viewed_user=self.user
        ).exists()
        
        if candidate_viewed_us:
            score *= 1.5
            
            recent_views = ProfileView.objects.filter(
                viewer=candidate,
                viewed_user=self.user,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-view_duration').first()
            
            if recent_views and recent_views.view_duration > 30:
                score *= 1.3
            if recent_views and recent_views.scrolled_to_bottom:
                score *= 1.2
        
        our_likes = ProfileLike.objects.filter(liker=self.user).values_list('liked_user_id', flat=True)
        their_likes = ProfileLike.objects.filter(liker=candidate).values_list('liked_user_id', flat=True)
        
        common_likes = set(our_likes) & set(their_likes)
        if common_likes:
            overlap_ratio = len(common_likes) / max(len(our_likes), 1)
            score *= (1 + overlap_ratio * 0.5)
        
        return min(score, 100)
    
    def _freshness_score(self, candidate):
        """Penalize profiles we've seen too often, boost new profiles"""
        from .models import ProfileView
        
        views_count = ProfileView.objects.filter(
            viewer=self.user,
            viewed_user=candidate
        ).count()
        
        if views_count == 0:
            return 100
        elif views_count == 1:
            return 80
        elif views_count <= 3:
            return 60
        elif views_count <= 5:
            return 40
        else:
            return 20
    
    def _activity_level_match(self, candidate):
        """Match users with similar activity patterns"""
        activity_map = {'low': 1, 'medium': 2, 'high': 3, 'very_high': 4}
        
        user_level = activity_map.get(self.user.activity_level, 2)
        candidate_level = activity_map.get(candidate.activity_level, 2)
        
        difference = abs(user_level - candidate_level)
        
        if difference == 0:
            return 100
        elif difference == 1:
            return 80
        elif difference == 2:
            return 60
        else:
            return 40
    
    def _calculate_profile_similarity(self, profile1, profile2):
        """Calculate similarity between two profiles (0-1 scale)"""
        similarity_score = 0
        factors = 0
        
        if profile1.user_interests and profile2.user_interests:
            interests1 = set(profile1.user_interests)
            interests2 = set(profile2.user_interests)
            if interests1 and interests2:
                jaccard = len(interests1 & interests2) / len(interests1 | interests2)
                similarity_score += jaccard
                factors += 1
        
        if profile1.year and profile2.year:
            age_diff = abs(int(profile1.year) - int(profile2.year))
            age_similarity = max(0, 1 - (age_diff / 20))
            similarity_score += age_similarity
            factors += 1
        
        if profile1.about and profile2.about:
            words1 = set(profile1.about.lower().split())
            words2 = set(profile2.about.lower().split())
            if words1 and words2:
                text_similarity = len(words1 & words2) / len(words1 | words2)
                similarity_score += text_similarity
                factors += 1
        
        return similarity_score / factors if factors > 0 else 0.5
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in km"""
        R = 6371
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calculate_profile_completeness(self, user):
        """Calculate how complete a profile is (0-1 scale)"""
        score = 0
        total = 10
        
        if user.profile_pic: score += 1
        if user.user_images and len(user.user_images) >= 3: score += 1
        if user.about and len(user.about) > 50: score += 1
        if user.user_interests and len(user.user_interests) >= 3: score += 1
        if user.first_name: score += 1
        if user.year: score += 1
        if user.religion: score += 1
        if user.instagram or user.twitter: score += 1
        if user.hopes: score += 1
        if user.latitude and user.longitude: score += 1
        
        return score / total
    
    def get_recommended_users(self, limit=20, exclude_ids=None):
        """
        Get recommended users sorted by compatibility score
        """
        from .models import User, ProfileLike, Match

        # Only recommend users with gender set and opposite gender
        candidates = User.objects.exclude(id=self.user.id).filter(gender__isnull=False).exclude(gender=self.user.gender)
        
        already_liked = ProfileLike.objects.filter(liker=self.user).values_list('liked_user_id', flat=True)
        candidates = candidates.exclude(id__in=already_liked)
        
        matches = Match.objects.filter(Q(user1=self.user) | Q(user2=self.user))
        matched_ids = []
        for match in matches:
            matched_ids.append(match.user2.id if match.user1 == self.user else match.user1.id)
        candidates = candidates.exclude(id__in=matched_ids)
        
        if exclude_ids:
            candidates = candidates.exclude(id__in=exclude_ids)
        
        scored_candidates = []
        for candidate in candidates[:100]:
            score = self.calculate_compatibility_score(candidate)
            scored_candidates.append((score, candidate))
        
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        return [candidate for score, candidate in scored_candidates[:limit]]
    
    def update_user_preferences(self):
        """
        Update user preference profile based on recent behavior
        Should be called periodically (e.g., after every 10 interactions)
        """
        from .models import UserInteraction, ProfileView, ProfileLike
        
        total_views = ProfileView.objects.filter(viewer=self.user).count()
        total_likes = ProfileLike.objects.filter(liker=self.user).count()
        
        if total_views > 0:
            self.preference_profile.swipe_rate = total_likes / total_views
        
        recent_interactions = UserInteraction.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if recent_interactions > 50:
            self.user.activity_level = 'very_high'
        elif recent_interactions > 25:
            self.user.activity_level = 'high'
        elif recent_interactions > 10:
            self.user.activity_level = 'medium'
        else:
            self.user.activity_level = 'low'
        
        engagement_factors = {
            'messages_sent': UserInteraction.objects.filter(
                user=self.user, interaction_type='message_sent'
            ).count(),
            'moments_created': self.user.moments.count(),
            'likes_given': total_likes,
            'profile_completeness': self._calculate_profile_completeness(self.user),
            'activity_consistency': self._calculate_activity_consistency()
        }
        
        self.user.engagement_score = (
            engagement_factors['messages_sent'] * 2 +
            engagement_factors['moments_created'] * 3 +
            engagement_factors['likes_given'] * 1 +
            engagement_factors['profile_completeness'] * 50 +
            engagement_factors['activity_consistency'] * 30
        )
        
        self.user.last_recommendation_update = timezone.now()
        self.user.save()
        self.preference_profile.save()
    
    def _calculate_activity_consistency(self):
        """Calculate how consistently user is active (0-1 scale)"""
        from .models import UserInteraction
        
        daily_activity = []
        for i in range(7):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = date.replace(hour=23, minute=59, second=59)
            
            count = UserInteraction.objects.filter(
                user=self.user,
                created_at__gte=day_start,
                created_at__lte=day_end
            ).count()
            
            daily_activity.append(min(count, 10))
        
        if not daily_activity:
            return 0
        
        mean = np.mean(daily_activity)
        if mean == 0:
            return 0
        
        std = np.std(daily_activity)
        cv = std / mean
        
        consistency = max(0, 1 - (cv / 2))
        
        return consistency