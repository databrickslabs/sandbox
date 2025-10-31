/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JudgeTraceResult } from './JudgeTraceResult';
/**
 * Result from running judge evaluation on traces.
 */
export type EvaluationResult = {
    /**
     * Judge identifier
     */
    judge_id: string;
    /**
     * Judge version used for evaluation
     */
    judge_version: number;
    /**
     * MLflow run ID for this evaluation
     */
    mlflow_run_id: string;
    /**
     * Individual trace evaluation results
     */
    evaluation_results: Array<JudgeTraceResult>;
    /**
     * Total number of traces evaluated
     */
    total_traces: number;
};

