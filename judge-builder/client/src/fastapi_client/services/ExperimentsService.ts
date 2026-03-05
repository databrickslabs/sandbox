/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ExperimentsService {
    /**
     * List Experiments
     * List available MLflow experiments.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listExperimentsApiExperimentsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/experiments/',
        });
    }
    /**
     * Get Experiment
     * Get experiment by ID.
     * @param experimentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getExperimentApiExperimentsExperimentIdGet(
        experimentId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/experiments/{experiment_id}',
            path: {
                'experiment_id': experimentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Experiment Traces
     * Get traces from experiment.
     * @param experimentId
     * @param runId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getExperimentTracesApiExperimentsExperimentIdTracesGet(
        experimentId: string,
        runId?: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/experiments/{experiment_id}/traces',
            path: {
                'experiment_id': experimentId,
            },
            query: {
                'run_id': runId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
