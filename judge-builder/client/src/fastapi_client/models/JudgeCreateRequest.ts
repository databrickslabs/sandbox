/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlignmentModelConfig } from './AlignmentModelConfig';
/**
 * Request model for creating a new judge.
 */
export type JudgeCreateRequest = {
    /**
     * Human-readable name for the judge
     */
    name: string;
    /**
     * Natural language evaluation criteria
     */
    instruction: string;
    /**
     * MLflow experiment ID to attach judge to
     */
    experiment_id: string;
    /**
     * Optional list of SME email addresses for labeling session
     */
    sme_emails?: (Array<string> | null);
    /**
     * Optional alignment model configuration
     */
    alignment_model_config?: (AlignmentModelConfig | null);
};

