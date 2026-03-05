/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Feedback } from './Feedback';
/**
 * Judge evaluation result for a specific trace.
 */
export type JudgeTraceResult = {
    /**
     * MLflow trace ID
     */
    trace_id: string;
    /**
     * Judge evaluation feedback (MLflow Feedback object)
     */
    feedback: Feedback;
    /**
     * Judge confidence score
     */
    confidence?: (number | null);
    /**
     * Judge version used for evaluation
     */
    judge_version: number;
};

