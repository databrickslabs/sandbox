/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssessmentError } from './AssessmentError';
import type { AssessmentSource } from './AssessmentSource';
import type { ExpectationValue } from './ExpectationValue';
import type { FeedbackValue } from './FeedbackValue';
export type Feedback = {
    name: string;
    source: AssessmentSource;
    trace_id?: (string | null);
    run_id?: (string | null);
    rationale?: (string | null);
    metadata?: (Record<string, string> | null);
    span_id?: (string | null);
    create_time_ms?: (number | null);
    last_update_time_ms?: (number | null);
    assessment_id?: (string | null);
    error?: (AssessmentError | null);
    expectation?: (ExpectationValue | null);
    feedback?: (FeedbackValue | null);
    overrides?: (string | null);
    valid?: (boolean | null);
};

