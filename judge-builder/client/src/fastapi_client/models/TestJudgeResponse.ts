/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Feedback } from './Feedback';
/**
 * Response model for testing a judge.
 */
export type TestJudgeResponse = {
    /**
     * MLflow trace ID that was tested
     */
    trace_id: string;
    /**
     * Judge evaluation feedback (MLflow Feedback object)
     */
    feedback: Feedback;
};

