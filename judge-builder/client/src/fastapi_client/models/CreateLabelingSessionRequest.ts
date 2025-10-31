/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for creating a labeling session.
 */
export type CreateLabelingSessionRequest = {
    /**
     * List of trace IDs to include in labeling session
     */
    trace_ids: Array<string>;
    /**
     * SME email addresses for labeling session
     */
    sme_emails: Array<string>;
};

