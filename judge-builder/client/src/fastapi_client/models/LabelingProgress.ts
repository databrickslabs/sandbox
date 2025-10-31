/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for labeling progress.
 */
export type LabelingProgress = {
    /**
     * Total number of examples
     */
    total_examples: number;
    /**
     * Number of labeled examples
     */
    labeled_examples: number;
    /**
     * Number used for alignment
     */
    used_for_alignment: number;
    /**
     * URL to labeling session
     */
    labeling_session_url?: (string | null);
    /**
     * SME email addresses assigned to labeling session
     */
    assigned_smes?: (Array<string> | null);
};

