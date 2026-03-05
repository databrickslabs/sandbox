/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for creating a labeling session.
 */
export type CreateLabelingSessionResponse = {
    /**
     * Labeling session identifier
     */
    session_id: string;
    /**
     * MLflow run ID for the labeling dataset
     */
    mlflow_run_id: string;
    /**
     * URL to the labeling interface
     */
    labeling_url: string;
    /**
     * When session was created
     */
    created_at: string;
};

