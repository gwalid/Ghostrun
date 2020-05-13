import datetime
import json

import gpxpy as gpxpy
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from .models import Category, Trip, Localisation


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


def index(request):
    return render(request, "front/index.html", context={})


@login_required()
def profile_home(request):
    categories = Category.objects.filter(user=request.user).prefetch_related("trips").all()
    bubbles_series = []
    for category in categories:
        data = []
        for trip in category.trips.filter(ended_at__isnull=False):
            data.append({'name': trip.short_name, 'value': int(trip.duration.seconds / 60), 'pk': trip.id})

        bubbles_series.append({'name': category.name,
                               'data': data})
    bubbles_series = json.dumps(bubbles_series)
    return render(request, "front/profile_home.html", context={"categories": categories, "bubbles_series": bubbles_series})


@login_required()
def my_settings_view(request):
    return HttpResponse("Page à creer")


class TripDetail(generic.DetailView):
    model = Trip
    context_object_name = "trip"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user).prefetch_related("localisations")

    def get_context_data(self, **kwargs):
        self.object: Trip
        context = super().get_context_data(**kwargs)

        map_coords = []
        for loc in self.object.localisations.all():
            map_coords.append({"lat": loc.latitude, "lng": loc.longitude})

        context['map_coords'] = json.dumps(map_coords)
        return context


def render_trip_to_gpxpy_object(trip):
    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    # Create points:
    loc: Localisation
    gpx_segment.points.extend([gpxpy.gpx.GPXTrackPoint(loc.latitude, loc.longitude, elevation=loc.altitude, time=loc.timestamp)
                               for loc in trip.localisations.all()])

    return gpx


class TripGPX(generic.DetailView):
    model = Trip
    context_object_name = "trip"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user).prefetch_related("localisations")

    def render_to_response(self, context, **response_kwargs):
        gpx = render_trip_to_gpxpy_object(self.get_object())
        return HttpResponse(gpx.to_xml(), content_type="text/xml; charset=utf-8")
