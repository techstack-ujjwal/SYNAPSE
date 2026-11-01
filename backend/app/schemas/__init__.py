"""Schemas package."""
from .patient import PatientIn
from .conversation import ConversationIn
from .report import SummaryIn, PrescriptionIn
from .report_extra import ReportComparisonIn, HandwrittenReportIn, GenerateReportIn, ReassignDoctorIn, CompleteConsultationIn
from .audio import AudioTranscribeIn, TextToSpeechIn
from .queue import QueueIn
from .doctor import DoctorIn

__all__ = [
    'PatientIn',
    'ConversationIn',
    'SummaryIn',
    'PrescriptionIn',
    'ReportComparisonIn',
    'HandwrittenReportIn',
    'GenerateReportIn',
    'ReassignDoctorIn',
    'CompleteConsultationIn',
    'AudioTranscribeIn',
    'TextToSpeechIn',
    'QueueIn',
    'DoctorIn',
]
