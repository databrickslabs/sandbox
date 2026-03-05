/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ServingEndpointsService {
    /**
     * List Serving Endpoints
     * List all serving endpoints in the workspace.
     * @param forceRefresh
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listServingEndpointsApiServingEndpointsGet(
        forceRefresh: boolean = false,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/serving-endpoints/',
            query: {
                'force_refresh': forceRefresh,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Serving Endpoint
     * Get details for a specific serving endpoint.
     * @param endpointName
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getServingEndpointApiServingEndpointsEndpointNameGet(
        endpointName: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/serving-endpoints/{endpoint_name}',
            path: {
                'endpoint_name': endpointName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Validate Endpoint
     * Validate that an endpoint exists.
     * @param endpointName
     * @returns any Successful Response
     * @throws ApiError
     */
    public static validateEndpointApiServingEndpointsEndpointNameValidatePost(
        endpointName: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/serving-endpoints/{endpoint_name}/validate',
            path: {
                'endpoint_name': endpointName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
