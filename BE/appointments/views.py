# BE/appointments/views.py
from rest_framework import status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Schedule, Appointment
from .serializers import ScheduleSerializer, AppointmentSerializer
from users.models import Doctor
from users.serializers import DoctorSerializer

# Doctor Schedule Management
class DoctorScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        if self.request.user.is_doctor:
            return Schedule.objects.filter(doctor__user=self.request.user)
        return Schedule.objects.none()

    def perform_create(self, serializer):
        doctor = Doctor.objects.get(user=self.request.user)
        serializer.save(doctor=doctor)

class DoctorScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        if self.request.user.is_doctor:
            return Schedule.objects.filter(doctor__user=self.request.user)
        return Schedule.objects.none()

# Patient Appointment Booking
class DoctorListView(generics.ListAPIView):
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['specialization', 'user__first_name', 'user__last_name']

    def get_queryset(self):
        return Doctor.objects.all()

class DoctorScheduleView(generics.ListAPIView):
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        doctor_id = self.kwargs.get('doctor_id')
        return Schedule.objects.filter(
            doctor_id=doctor_id,
            date__gte=datetime.now().date(),
            is_available=True
        )

class BookAppointmentView(APIView):
    def post(self, request):
        if not request.user.is_patient:
            return Response({"detail": "Only patients can book appointments"},
                            status=status.HTTP_403_FORBIDDEN)

        from users.models import Patient
        patient = Patient.objects.get(user=request.user)

        # Get schedule and validate
        schedule_id = request.data.get('schedule_id')
        slot_time = request.data.get('time')  # Time for the specific slot

        try:
            schedule = Schedule.objects.get(id=schedule_id, is_available=True)
        except Schedule.DoesNotExist:
            return Response({"detail": "Schedule not found or not available"},
                            status=status.HTTP_404_NOT_FOUND)

        # Calculate end time based on slot duration
        start_time = datetime.strptime(slot_time, '%H:%M').time()
        end_time_dt = datetime.combine(datetime.today(), start_time) + timedelta(minutes=schedule.slot_duration)
        end_time = end_time_dt.time()

        # Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=schedule.doctor,
            schedule=schedule,
            date=schedule.date,
            time=start_time,
            end_time=end_time,
            reason=request.data.get('reason', '')
        )

        # If this slot makes the schedule fully booked, mark it unavailable
        if not self._has_available_slots(schedule):
            schedule.is_available = False
            schedule.save()

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    def _has_available_slots(self, schedule):
        # Check if there are still available time slots in this schedule
        booked_slots = Appointment.objects.filter(
            schedule=schedule,
            status='CONFIRMED'
        ).count()

        total_minutes = (datetime.combine(datetime.min, schedule.end_time) -
                         datetime.combine(datetime.min, schedule.start_time)).seconds / 60
        total_slots = total_minutes / schedule.slot_duration

        return booked_slots < total_slots

# Patient Appointment Management
class PatientAppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        if self.request.user.is_patient:
            from users.models import Patient
            patient = Patient.objects.get(user=self.request.user)
            return Appointment.objects.filter(patient=patient)
        return Appointment.objects.none()

# Doctor Appointment Management
class DoctorAppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        if self.request.user.is_doctor:
            doctor = Doctor.objects.get(user=self.request.user)
            return Appointment.objects.filter(doctor=doctor)
        return Appointment.objects.none()

# Appointment Cancellation (for both doctor and patient)
class CancelAppointmentView(APIView):
    def patch(self, request, appointment_id):
        try:
            if request.user.is_doctor:
                appointment = Appointment.objects.get(
                    id=appointment_id,
                    doctor__user=request.user
                )
            elif request.user.is_patient:
                appointment = Appointment.objects.get(
                    id=appointment_id,
                    patient__user=request.user
                )
            else:
                return Response({"detail": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            appointment.status = 'CANCELLED'
            appointment.save()

            # If this was the only booked slot, make schedule available again
            self._update_schedule_availability(appointment.schedule)

            return Response(AppointmentSerializer(appointment).data)

        except Appointment.DoesNotExist:
            return Response({"detail": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

    def _update_schedule_availability(self, schedule):
        active_appointments = Appointment.objects.filter(
            schedule=schedule,
            status='CONFIRMED'
        ).count()

        if active_appointments == 0:
            schedule.is_available = True
            schedule.save()