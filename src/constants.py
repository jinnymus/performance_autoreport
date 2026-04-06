"""
Test type constants (aligned with common performance-reporting APIs).
"""
MAX_PERFORMANCE_SEARCH = 'max_performance_search'
MAX_PERFORMANCE_CONFIRMATION = 'max_performance_confirmation'
DEV = 'dev'
WIREMOCK = 'wiremock'
CLINICJS = 'clinicjs'
STABILITY = 'stability'
TOP_TIME = 'top_time'

TEST_TYPES = (
    MAX_PERFORMANCE_SEARCH,
    MAX_PERFORMANCE_CONFIRMATION,
    DEV,
    WIREMOCK,
    CLINICJS,
    STABILITY,
    TOP_TIME,
)

# Types for which max RPS is computed (stepwise search, SLA ≤ 400 ms).
MAX_RPS_CALCULATION_TYPES = (MAX_PERFORMANCE_SEARCH,)

TEST_TYPE_LABELS = {
    MAX_PERFORMANCE_SEARCH: 'Maximum performance search',
    MAX_PERFORMANCE_CONFIRMATION: 'Maximum performance confirmation',
    DEV: 'Development build',
    WIREMOCK: 'With WireMock',
    CLINICJS: 'Clinic.js report collection',
    STABILITY: 'Stability test',
    TOP_TIME: 'Top time test',
}
